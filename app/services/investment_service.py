from datetime import date

from app.extensions import db
from app.models.asset import Asset
from app.models.expense import Expense
from app.models.income import Income
from app.models.investment_event import InvestmentEvent
from app.services.dashboard_service import DashboardService


class InvestmentService:
    """Authoritative business logic for investment funding, valuation and liquidation."""

    EPSILON = 1e-9

    @staticmethod
    def available_cash(user_id, exclude_expense_id=None):
        return DashboardService.available_balance(user_id, exclude_expense_id=exclude_expense_id)

    @staticmethod
    def create(user, *, name, investment_type, acquisition_date, amount, current_value=None, quantity=None, notes=None):
        from app.subscriptions.service import SubscriptionService

        amount = float(amount or 0)
        if amount <= 0:
            raise ValueError("Investment amount must be greater than zero.")
        if not acquisition_date:
            acquisition_date = date.today()
        current_value = amount if current_value is None else float(current_value)
        if current_value < 0:
            raise ValueError("Investment current value cannot be negative.")
        if current_value > amount:
            # Initial excess is an investment gain; it is not silently added to cost basis.
            initial_gain = current_value - amount
        else:
            initial_gain = current_value - amount

        allowed, message = SubscriptionService.can_add_transaction(user.id)
        if not allowed:
            raise ValueError(message)

        available = DashboardService.available_balance(user.id, as_of=acquisition_date)
        if amount > available + InvestmentService.EPSILON:
            raise ValueError(f"Insufficient available balance. Available balance is {available:,.2f}.")

        expense = Expense(
            user_id=user.id,
            category="Investment",
            merchant=(name or "Investment")[:150],
            description=f"Investment funding: {name}",
            amount=amount,
            payment_method="Internal Investment Funding",
            expense_date=acquisition_date,
            notes=notes,
            recurring=False,
            transaction_class="investment",
        )
        db.session.add(expense)
        db.session.flush()

        asset = Asset(
            user_id=user.id,
            name=(name or "Investment").strip()[:160],
            asset_type="Investment",
            investment_type=(investment_type or "Investment").strip()[:100],
            acquisition_date=acquisition_date,
            acquisition_cost=amount,
            current_value=current_value,
            quantity=quantity,
            cost_basis=amount,
            currency=user.currency or "NGN",
            notes=notes,
            source_expense_id=expense.id,
        )
        db.session.add(asset)
        db.session.flush()

        event = InvestmentEvent(
            asset_id=asset.id,
            user_id=user.id,
            event_type="funding",
            event_date=acquisition_date,
            amount=amount,
            previous_value=0,
            new_value=amount,
            cost_basis_change=amount,
            notes=notes,
        )
        db.session.add(event)

        # If the initial valuation differs from cost, recognize the difference immediately.
        if abs(initial_gain) > InvestmentService.EPSILON:
            if initial_gain > 0:
                income = Income(
                    user_id=user.id,
                    source=asset.name,
                    category="Investment Gain",
                    amount=initial_gain,
                    received_date=acquisition_date,
                    notes="Initial investment valuation gain recognized at acquisition.",
                    recurring=False,
                    transaction_class="investment_gain",
                )
                db.session.add(income)
                db.session.flush()
                valuation_event = InvestmentEvent(
                    asset_id=asset.id, user_id=user.id, event_type="valuation",
                    event_date=acquisition_date, amount=abs(initial_gain),
                    previous_value=amount, new_value=current_value,
                    realized_gain_loss=initial_gain, income_id=income.id, notes=income.notes
                )
                db.session.add(valuation_event)
            else:
                loss = Expense(
                    user_id=user.id,
                    category="Investment Loss",
                    merchant=asset.name,
                    description="Initial investment valuation loss",
                    amount=abs(initial_gain),
                    payment_method="Investment Valuation",
                    expense_date=acquisition_date,
                    notes="Initial investment valuation loss recognized at acquisition.",
                    recurring=False,
                    transaction_class="investment_loss",
                )
                db.session.add(loss)
                db.session.flush()
                valuation_event = InvestmentEvent(
                    asset_id=asset.id, user_id=user.id, event_type="valuation",
                    event_date=acquisition_date, amount=abs(initial_gain),
                    previous_value=amount, new_value=current_value,
                    realized_gain_loss=initial_gain, expense_id=loss.id, notes=loss.notes
                )
                db.session.add(valuation_event)

        db.session.commit()
        return asset

    @staticmethod
    def update_valuation(user, asset, *, new_value, event_date, notes=None):
        if asset.user_id != user.id or not asset.is_investment or not asset.is_active:
            raise ValueError("Invalid or inactive investment record.")
        new_value = float(new_value)
        if new_value < 0:
            raise ValueError("Investment current value cannot be negative.")
        old_value = float(asset.current_value or 0)
        delta = new_value - old_value
        asset.current_value = new_value

        if abs(delta) > InvestmentService.EPSILON:
            event = InvestmentEvent(
                asset_id=asset.id,
                user_id=user.id,
                event_type="valuation",
                event_date=event_date,
                amount=abs(delta),
                previous_value=old_value,
                new_value=new_value,
                cost_basis_change=0,
                realized_gain_loss=delta,
                notes=notes,
            )
            db.session.add(event)
            if delta > 0:
                income = Income(
                    user_id=user.id,
                    source=asset.name,
                    category="Investment Gain",
                    amount=delta,
                    received_date=event_date,
                    notes=notes or "Investment valuation gain.",
                    recurring=False,
                    transaction_class="investment_gain",
                )
                db.session.add(income)
                db.session.flush()
                event.income_id = income.id
            else:
                expense = Expense(
                    user_id=user.id,
                    category="Investment Loss",
                    merchant=asset.name,
                    description="Investment valuation loss",
                    amount=abs(delta),
                    payment_method="Investment Valuation",
                    expense_date=event_date,
                    notes=notes or "Investment valuation loss.",
                    recurring=False,
                    transaction_class="investment_loss",
                )
                db.session.add(expense)
                db.session.flush()
                event.expense_id = expense.id
        db.session.commit()
        return asset

    @staticmethod
    def liquidate(user, asset, *, amount, liquidation_date, notes=None):
        if asset.user_id != user.id:
            raise ValueError("Invalid investment record.")
        if not asset.is_investment:
            raise ValueError("Only investment assets can be liquidated.")
        if not asset.is_active:
            raise ValueError("This investment is already fully liquidated.")

        proceeds = float(amount or 0)
        current_value = float(asset.current_value or 0)
        cost_basis = float(asset.cost_basis if asset.cost_basis is not None else asset.acquisition_cost or 0)
        if proceeds <= 0:
            raise ValueError("Liquidation amount must be greater than zero.")
        if proceeds > current_value + InvestmentService.EPSILON:
            raise ValueError("Liquidation amount cannot exceed the investment's current value.")
        if not liquidation_date:
            liquidation_date = date.today()

        ratio = proceeds / current_value if current_value > 0 else 0
        allocated_cost = cost_basis * ratio
        realized_gain_loss = proceeds - allocated_cost
        carrying_value_released = proceeds
        realization_adjustment = 0.0

        # Valuation changes have already been recognized as income/expense when
        # the carrying value changed. Therefore liquidation only recognizes any
        # difference between actual proceeds and the current carrying value,
        # preventing previously recognized gains/losses from being counted again.
        # Liquidation is an actual cash inflow. It is classified separately from
        # profit so the reports can distinguish returned capital from investment performance.
        liquidation_income_amount = proceeds
        income = Income(
            user_id=user.id,
            source=asset.name,
            category="Investment Liquidation",
            amount=liquidation_income_amount,
            received_date=liquidation_date,
            notes=notes or "Return of investment capital from liquidation.",
            recurring=False,
            transaction_class="investment_liquidation",
        )
        db.session.add(income)
        db.session.flush()

        event = InvestmentEvent(
            asset_id=asset.id,
            user_id=user.id,
            event_type="liquidation",
            event_date=liquidation_date,
            amount=proceeds,
            previous_value=current_value,
            new_value=current_value - proceeds,
            cost_basis_change=-allocated_cost,
            realized_gain_loss=realized_gain_loss,
            proceeds=proceeds,
            income_id=income.id,
            notes=notes,
        )
        db.session.add(event)

        remaining_value = current_value - proceeds
        remaining_cost = max(cost_basis - allocated_cost, 0)
        asset.current_value = remaining_value
        asset.cost_basis = remaining_cost
        asset.acquisition_cost = max(float(asset.acquisition_cost or 0) - allocated_cost, 0)

        # If the actual proceeds differ from the carrying value being removed,
        # recognize only that new realization adjustment.
        realization_adjustment = proceeds - carrying_value_released
        if abs(realization_adjustment) > InvestmentService.EPSILON:
            if realization_adjustment > 0:
                gain = Income(
                    user_id=user.id,
                    source=asset.name,
                    category="Investment Gain",
                    amount=realization_adjustment,
                    received_date=liquidation_date,
                    notes="Additional realized investment gain on liquidation.",
                    recurring=False,
                    transaction_class="investment_gain",
                )
                db.session.add(gain)
            else:
                loss = Expense(
                    user_id=user.id,
                    category="Investment Loss",
                    merchant=asset.name,
                    description="Additional realized investment loss on liquidation",
                    amount=abs(realization_adjustment),
                    payment_method="Investment Liquidation",
                    expense_date=liquidation_date,
                    notes="Additional realized investment loss on liquidation.",
                    recurring=False,
                    transaction_class="investment_loss",
                )
                db.session.add(loss)

        if remaining_value <= InvestmentService.EPSILON:
            asset.current_value = 0
            asset.cost_basis = 0
            asset.acquisition_cost = 0
            asset.is_active = False

        db.session.commit()
        return asset
