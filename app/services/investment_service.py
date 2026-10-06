from datetime import date

from app.extensions import db
from app.models.asset import Asset
from app.models.expense import Expense
from app.models.income import Income
from app.models.investment_event import InvestmentEvent


class InvestmentService:
    """
    Authoritative business logic for investment funding, valuation,
    revaluation, liquidation and valuation reversal.

    Accounting rules:
        - Investment funding/cost = expense
        - Goal contributions are handled by the goal service as expenses
        - Investment liquidation proceeds = income
        - Investment valuation/revaluation is non-cash and is never an
          Income or Expense transaction
        - Valuation/revaluation changes update the investment carrying value
          and remain in investment gain/loss only
        - Reversed valuation/revaluation events are permanently removed
    """

    EPSILON = 1e-9

    @staticmethod
    def available_cash(user_id, exclude_expense_id=None, as_of=None):
        """
        Compatibility wrapper.

        Available balance is derived from cumulative monthly savings through
        DashboardService. This method does not maintain an independent balance.
        """
        from app.services.dashboard_service import DashboardService

        return DashboardService.available_balance(
            user_id,
            exclude_expense_id=exclude_expense_id,
            as_of=as_of,
        )

    # ==========================================================
    # CREATE INVESTMENT
    # ==========================================================

    @staticmethod
    def create(
        user,
        *,
        name,
        investment_type,
        acquisition_date,
        amount,
        current_value=None,
        quantity=None,
        notes=None,
    ):
        from app.subscriptions.service import SubscriptionService

        amount = float(amount or 0)

        if amount <= 0:
            raise ValueError("Investment amount must be greater than zero.")

        if not acquisition_date:
            acquisition_date = date.today()

        current_value = (
            amount
            if current_value is None
            else float(current_value)
        )

        if current_value < 0:
            raise ValueError(
                "Investment current value cannot be negative."
            )

        allowed, message = SubscriptionService.can_add_transaction(
            user.id
        )

        if not allowed:
            raise ValueError(message)

        available = InvestmentService.available_cash(
            user.id,
            as_of=acquisition_date,
        )

        if amount > available + InvestmentService.EPSILON:
            raise ValueError(
                f"Insufficient available balance. "
                f"Available balance is {available:,.2f}."
            )

        investment_name = (
            (name or "Investment").strip()[:160]
        )

        # ------------------------------------------------------
        # Investment funding is an expense.
        # ------------------------------------------------------

        expense = Expense(
            user_id=user.id,
            category="Investment",
            merchant=investment_name[:150],
            description=f"Investment funding: {investment_name}",
            amount=amount,
            payment_method="Internal Investment Funding",
            expense_date=acquisition_date,
            notes=notes,
            recurring=False,
            transaction_class="investment",
        )

        db.session.add(expense)
        db.session.flush()

        # ------------------------------------------------------
        # Investment asset
        # ------------------------------------------------------

        asset = Asset(
            user_id=user.id,
            name=investment_name,
            asset_type="Investment",
            investment_type=(
                (investment_type or "Investment").strip()[:100]
            ),
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

        # ------------------------------------------------------
        # Funding event
        # ------------------------------------------------------

        funding_event = InvestmentEvent(
            asset_id=asset.id,
            user_id=user.id,
            event_type="funding",
            event_date=acquisition_date,
            amount=amount,
            previous_value=0,
            new_value=amount,
            cost_basis_change=amount,
            realized_gain_loss=0,
            proceeds=0,
            notes=notes,
        )

        db.session.add(funding_event)

        # ------------------------------------------------------
        # Initial valuation difference.
        #
        # This is an investment carrying-value adjustment, not cash.
        # It must NEVER create an Income or Expense record.
        # The difference remains entirely inside the investment asset
        # and its valuation event.
        # ------------------------------------------------------

        initial_difference = current_value - amount

        if abs(initial_difference) > InvestmentService.EPSILON:
            valuation_event = InvestmentEvent(
                asset_id=asset.id,
                user_id=user.id,
                event_type="valuation",
                event_date=acquisition_date,
                amount=abs(initial_difference),
                previous_value=amount,
                new_value=current_value,
                cost_basis_change=0,
                realized_gain_loss=initial_difference,
                proceeds=0,
                notes=(
                    notes
                    or "Initial investment valuation adjustment."
                ),
            )

            db.session.add(valuation_event)

        db.session.commit()

        return asset

    # ==========================================================
    # UPDATE / REVALUE INVESTMENT
    # ==========================================================

    @staticmethod
    def update_valuation(
        user,
        asset,
        *,
        new_value,
        event_date,
        notes=None,
    ):
        if (
            asset.user_id != user.id
            or not asset.is_investment
            or not asset.is_active
        ):
            raise ValueError(
                "Invalid or inactive investment record."
            )

        new_value = float(new_value)

        if new_value < 0:
            raise ValueError(
                "Investment current value cannot be negative."
            )

        if not event_date:
            event_date = date.today()

        old_value = float(
            asset.current_value or 0
        )

        delta = new_value - old_value

        # Nothing changed.
        if abs(delta) <= InvestmentService.EPSILON:
            asset.current_value = new_value
            db.session.commit()
            return asset

        # ------------------------------------------------------
        # Update carrying value first.
        # ------------------------------------------------------

        asset.current_value = new_value

        # ------------------------------------------------------
        # Valuation/revaluation is non-cash.
        #
        # Do NOT create Income or Expense rows here. The change belongs
        # only to the investment carrying value and investment event.
        # ------------------------------------------------------

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
            proceeds=0,
            notes=notes or "Investment valuation adjustment.",
        )

        db.session.add(event)

        db.session.commit()

        return asset

    # ==========================================================
    # REVERSE VALUATION / REVALUATION
    # ==========================================================

    @staticmethod
    def reverse_valuation(
        user,
        asset,
        event_id,
    ):
        """
        Permanently reverse the selected valuation/revaluation.

        The operation is deliberately restricted to a valuation event that
        has no later investment event affecting the same asset.

        This guarantees that removing the valuation cannot corrupt subsequent
        valuation or liquidation calculations.

        The valuation event is permanently deleted. Valuation changes have
        no linked Income or Expense record because they are non-cash.

        The asset current value is restored to the valuation event's
        previous value.

        No reversal transaction is created.
        """

        if asset.user_id != user.id:
            raise ValueError(
                "Invalid investment record."
            )

        if not asset.is_investment:
            raise ValueError(
                "Only investment assets support valuation reversal."
            )

        event = (
            InvestmentEvent.query
            .filter_by(
                id=event_id,
                asset_id=asset.id,
                user_id=user.id,
            )
            .first()
        )

        if not event:
            raise ValueError(
                "Investment valuation event not found."
            )

        if event.event_type != "valuation":
            raise ValueError(
                "Only valuation or revaluation events can be reversed."
            )

        # ------------------------------------------------------
        # Only the latest investment event can be safely reversed.
        # ------------------------------------------------------

        later_event = (
            InvestmentEvent.query
            .filter(
                InvestmentEvent.asset_id == asset.id,
                InvestmentEvent.user_id == user.id,
                (
                    (InvestmentEvent.event_date > event.event_date)
                    |
                    (
                        (InvestmentEvent.event_date == event.event_date)
                        &
                        (InvestmentEvent.id > event.id)
                    )
                ),
            )
            .order_by(
                InvestmentEvent.event_date.asc(),
                InvestmentEvent.id.asc(),
            )
            .first()
        )

        if later_event:
            raise ValueError(
                "This valuation cannot be reversed because a later "
                f"{later_event.event_type} event already depends on it. "
                "Reverse later investment events first."
            )

        previous_value = float(
            event.previous_value or 0
        )

        # ------------------------------------------------------
        # Valuation events have no Income/Expense record.
        #
        # For databases migrated from an older FOCOST version, clear
        # any legacy links defensively before deleting the event.
        # ------------------------------------------------------

        asset.current_value = previous_value

        if event.income_id or event.expense_id:
            event.income_id = None
            event.expense_id = None

        db.session.delete(event)

        db.session.commit()

        return asset

    # ==========================================================
    # LIQUIDATION
    # ==========================================================

    @staticmethod
    def liquidate(
        user,
        asset,
        *,
        amount,
        liquidation_date,
        notes=None,
    ):
        if asset.user_id != user.id:
            raise ValueError(
                "Invalid investment record."
            )

        if not asset.is_investment:
            raise ValueError(
                "Only investment assets can be liquidated."
            )

        if not asset.is_active:
            raise ValueError(
                "This investment is already fully liquidated."
            )

        proceeds = float(amount or 0)

        current_value = float(
            asset.current_value or 0
        )

        cost_basis = float(
            asset.cost_basis
            if asset.cost_basis is not None
            else asset.acquisition_cost or 0
        )

        if proceeds <= 0:
            raise ValueError(
                "Liquidation amount must be greater than zero."
            )

        if proceeds > current_value + InvestmentService.EPSILON:
            raise ValueError(
                "Liquidation amount cannot exceed the investment's "
                "current value."
            )

        if not liquidation_date:
            liquidation_date = date.today()

        # ------------------------------------------------------
        # Allocate cost basis proportionally to the portion sold.
        # ------------------------------------------------------

        ratio = (
            proceeds / current_value
            if current_value > InvestmentService.EPSILON
            else 0
        )

        allocated_cost = cost_basis * ratio

        realized_gain_loss = (
            proceeds - allocated_cost
        )

        remaining_value = max(
            current_value - proceeds,
            0,
        )

        remaining_cost = max(
            cost_basis - allocated_cost,
            0,
        )

        remaining_acquisition_cost = max(
            float(asset.acquisition_cost or 0)
            - allocated_cost,
            0,
        )

        # ------------------------------------------------------
        # Liquidation proceeds are income.
        # ------------------------------------------------------

        income = Income(
            user_id=user.id,
            source=asset.name,
            category="Investment Liquidation",
            amount=proceeds,
            received_date=liquidation_date,
            notes=(
                notes
                or "Return of investment capital from liquidation."
            ),
            recurring=False,
            transaction_class="investment_liquidation",
        )

        db.session.add(income)
        db.session.flush()

        # ------------------------------------------------------
        # Liquidation event.
        # ------------------------------------------------------

        event = InvestmentEvent(
            asset_id=asset.id,
            user_id=user.id,
            event_type="liquidation",
            event_date=liquidation_date,
            amount=proceeds,
            previous_value=current_value,
            new_value=remaining_value,
            cost_basis_change=-allocated_cost,
            realized_gain_loss=realized_gain_loss,
            proceeds=proceeds,
            income_id=income.id,
            notes=notes,
        )

        db.session.add(event)

        # ------------------------------------------------------
        # Update remaining holding.
        # ------------------------------------------------------

        asset.current_value = remaining_value
        asset.cost_basis = remaining_cost
        asset.acquisition_cost = remaining_acquisition_cost

        if remaining_value <= InvestmentService.EPSILON:
            asset.current_value = 0
            asset.cost_basis = 0
            asset.acquisition_cost = 0
            asset.is_active = False

        db.session.commit()

        return asset

    # ==========================================================
    # REVERSE LIQUIDATION
    # ==========================================================

    @staticmethod
    def reverse_liquidation(
        user,
        asset,
        event_id,
    ):
        """
        Permanently reverse a partial or full investment liquidation.

        The liquidation can only be reversed when it is the latest
        investment event for the asset. This prevents the reversal from
        invalidating later valuation, revaluation, or liquidation events.

        The reversal permanently removes:

            - the liquidation event
            - the linked Investment Liquidation income

        The investment is restored to exactly the state represented by
        the liquidation event's previous value and cost-basis allocation.

        For a full liquidation, the investment is also reactivated.

        No compensating income, expense, or reversal transaction is created.
        """

        if asset.user_id != user.id:
            raise ValueError(
                "Invalid investment record."
            )

        if not asset.is_investment:
            raise ValueError(
                "Only investment assets support liquidation reversal."
            )

        event = (
            InvestmentEvent.query
            .filter_by(
                id=event_id,
                asset_id=asset.id,
                user_id=user.id,
            )
            .first()
        )

        if not event:
            raise ValueError(
                "Investment liquidation event not found."
            )

        if event.event_type != "liquidation":
            raise ValueError(
                "Only liquidation events can be reversed."
            )

        # ------------------------------------------------------
        # Only the latest investment event can be safely reversed.
        #
        # This is the same chronological rule used by valuation
        # reversal. Events on the same date are ordered by ID.
        # ------------------------------------------------------

        later_event = (
            InvestmentEvent.query
            .filter(
                InvestmentEvent.asset_id == asset.id,
                InvestmentEvent.user_id == user.id,
                (
                    (InvestmentEvent.event_date > event.event_date)
                    |
                    (
                        (InvestmentEvent.event_date == event.event_date)
                        &
                        (InvestmentEvent.id > event.id)
                    )
                ),
            )
            .order_by(
                InvestmentEvent.event_date.asc(),
                InvestmentEvent.id.asc(),
            )
            .first()
        )

        if later_event:
            raise ValueError(
                "This liquidation cannot be reversed because a later "
                f"{later_event.event_type} event already depends on it. "
                "Reverse later investment events first."
            )

        # ------------------------------------------------------
        # Capture the exact pre-liquidation state.
        #
        # The liquidation event stores previous_value, while the
        # cost-basis change stores the amount removed from the
        # holding. Therefore:
        #
        #   previous cost basis
        #       = current cost basis - cost_basis_change
        #
        # Because cost_basis_change is negative for liquidation,
        # this correctly adds the allocated cost basis back.
        # ------------------------------------------------------

        previous_value = float(
            event.previous_value or 0
        )

        current_cost_basis = float(
            asset.cost_basis
            if asset.cost_basis is not None
            else 0
        )

        current_acquisition_cost = float(
            asset.acquisition_cost or 0
        )

        cost_basis_change = float(
            event.cost_basis_change or 0
        )

        restored_cost_basis = (
            current_cost_basis - cost_basis_change
        )

        restored_acquisition_cost = (
            current_acquisition_cost - cost_basis_change
        )

        # ------------------------------------------------------
        # Prevent floating-point residue from creating tiny
        # artificial balances such as 0.0000000001.
        # ------------------------------------------------------

        if abs(restored_cost_basis) <= InvestmentService.EPSILON:
            restored_cost_basis = 0.0

        if abs(restored_acquisition_cost) <= InvestmentService.EPSILON:
            restored_acquisition_cost = 0.0

        if abs(previous_value) <= InvestmentService.EPSILON:
            previous_value = 0.0

        # ------------------------------------------------------
        # Retrieve the linked liquidation income.
        # ------------------------------------------------------

        linked_income = None

        if event.income_id:
            linked_income = db.session.get(
                Income,
                event.income_id,
            )

        # ------------------------------------------------------
        # Restore the investment to its exact pre-liquidation
        # carrying state.
        # ------------------------------------------------------

        asset.current_value = previous_value
        asset.cost_basis = restored_cost_basis
        asset.acquisition_cost = restored_acquisition_cost

        # A liquidation that reduced the investment to zero sets
        # is_active=False. Reversal must reactivate it.
        asset.is_active = True

        # ------------------------------------------------------
        # Delete the financial transaction first.
        #
        # No compensating income is created. The original
        # liquidation proceeds are completely removed.
        # ------------------------------------------------------

        if linked_income is not None:
            db.session.delete(linked_income)

        # ------------------------------------------------------
        # Delete the liquidation event itself.
        # ------------------------------------------------------

        db.session.delete(event)

        db.session.commit()

        return asset