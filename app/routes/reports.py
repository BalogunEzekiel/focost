# app/routes/reports.py

@reports_bp.route("/transactions")
@login_required
def transactions():
    transactions = DashboardService.recent_transactions(current_user.id)

    return render_template(
        "reports/transactions.html",
        transactions=transactions
    )