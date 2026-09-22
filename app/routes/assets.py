from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.asset import Asset
from app.services.investment_service import InvestmentService

assets_bp = Blueprint("assets", __name__, url_prefix="/assets")


@assets_bp.get("/")
@login_required
def index():
    assets = Asset.query.filter_by(user_id=current_user.id, is_active=True).order_by(Asset.current_value.desc()).all()
    investments = [a for a in assets if a.is_investment]
    investment_history = (
        Asset.query
        .filter_by(user_id=current_user.id, is_active=False)
        .filter(Asset.asset_type.ilike("investment"))
        .order_by(Asset.updated_at.desc())
        .all()
    )
    total_cost = sum(float(a.cost_basis if a.cost_basis is not None else a.acquisition_cost or 0) for a in investments)
    total_value = sum(float(a.current_value or 0) for a in investments)
    return render_template(
        "assets/index.html",
        today=date.today().isoformat(),
        assets=assets,
        investments=investments,
        investment_history=investment_history,
        total_cost=total_cost,
        total_value=total_value,
        gain_loss=total_value - total_cost,
    )


@assets_bp.post("/create")
@login_required
def create():
    try:
        name = request.form["name"].strip()
        asset_type = request.form["asset_type"].strip()
        acquisition_date = request.form.get("acquisition_date") or None
        parsed_date = date.fromisoformat(acquisition_date) if acquisition_date else date.today()
        amount = float(request.form.get("acquisition_cost", 0) or 0)
        current_value = float(request.form.get("current_value", amount) or amount)
        quantity = float(request.form["quantity"]) if request.form.get("quantity") else None
        notes = request.form.get("notes", "").strip() or None

        if asset_type.lower() == "investment":
            InvestmentService.create(
                current_user,
                name=name,
                investment_type=request.form.get("investment_type", "").strip() or "Investment",
                acquisition_date=parsed_date,
                amount=amount,
                current_value=current_value,
                quantity=quantity,
                notes=notes,
            )
            flash("Investment created and funded from your available balance.", "success")
        else:
            asset = Asset(
                user_id=current_user.id,
                name=name,
                asset_type=asset_type,
                investment_type=request.form.get("investment_type", "").strip() or None,
                acquisition_date=parsed_date,
                acquisition_cost=amount,
                current_value=current_value,
                quantity=quantity,
                cost_basis=float(request.form["cost_basis"]) if request.form.get("cost_basis") else None,
                currency=current_user.currency or "NGN",
                notes=notes,
            )
            db.session.add(asset)
            db.session.commit()
            flash("Asset added successfully.", "success")
    except (KeyError, ValueError) as exc:
        db.session.rollback()
        flash(str(exc) or "Please provide valid investment information.", "danger")
    return redirect(url_for("assets.index"))


@assets_bp.route("/<int:asset_id>/edit", methods=["GET", "POST"])
@login_required
def edit(asset_id):
    asset = Asset.query.filter_by(id=asset_id, user_id=current_user.id, is_active=True).first_or_404()
    if request.method == "POST":
        try:
            asset.name = request.form["name"].strip()
            asset.investment_type = request.form.get("investment_type", "").strip() or asset.investment_type
            asset.quantity = float(request.form["quantity"]) if request.form.get("quantity") else asset.quantity
            asset.notes = request.form.get("notes", "").strip() or None
            if asset.is_investment:
                new_value = float(request.form.get("current_value", asset.current_value) or 0)
                event_date = date.fromisoformat(request.form["valuation_date"]) if request.form.get("valuation_date") else date.today()
                InvestmentService.update_valuation(
                    current_user,
                    asset,
                    new_value=new_value,
                    event_date=event_date,
                    notes=asset.notes,
                )
                flash("Investment updated and the valuation change was recorded.", "success")
            else:
                asset.asset_type = request.form["asset_type"].strip()
                asset.acquisition_date = date.fromisoformat(request.form["acquisition_date"]) if request.form.get("acquisition_date") else None
                asset.current_value = float(request.form.get("current_value", 0) or 0)
                db.session.commit()
                flash("Asset updated successfully.", "success")
            return redirect(url_for("assets.index"))
        except (KeyError, ValueError) as exc:
            db.session.rollback()
            flash(str(exc) or "Please provide valid investment information.", "danger")
    return render_template("assets/edit.html", asset=asset)


@assets_bp.post("/<int:asset_id>/liquidate")
@login_required
def liquidate(asset_id):
    asset = Asset.query.filter_by(id=asset_id, user_id=current_user.id, is_active=True).first_or_404()
    try:
        amount = float(request.form.get("amount", 0) or 0)
        liquidation_date = date.fromisoformat(request.form["liquidation_date"]) if request.form.get("liquidation_date") else date.today()
        InvestmentService.liquidate(
            current_user,
            asset,
            amount=amount,
            liquidation_date=liquidation_date,
            notes=request.form.get("notes", "").strip() or None,
        )
        flash("Investment liquidation recorded successfully. The proceeds are now available.", "success")
    except (KeyError, ValueError) as exc:
        db.session.rollback()
        flash(str(exc) or "Unable to liquidate this investment.", "danger")
    return redirect(url_for("assets.index"))


@assets_bp.post("/<int:asset_id>/delete")
@login_required
def delete(asset_id):
    asset = Asset.query.filter_by(id=asset_id, user_id=current_user.id, is_active=True).first_or_404()
    if asset.is_investment:
        flash("Investments cannot be deleted. Use partial or full liquidation to close an investment while preserving its history.", "warning")
    else:
        asset.is_active = False
        db.session.commit()
        flash("Asset removed from your active portfolio.", "success")
    return redirect(url_for("assets.index"))
