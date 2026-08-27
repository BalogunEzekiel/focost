from datetime import datetime

from flask import (
    render_template,
    request,
    send_file,
    flash,
    redirect,
    url_for,
)

from flask_login import (
    login_required,
    current_user,
)

from app.reports import reports_bp
from app.reports.services import ReportService
from app.reports.exports import ExportService


# ==========================================================
# FILTER PARSING
# ==========================================================

def _filters():
    """
    Parse and validate report filters from the query string.

    Returns:
        start_date_text,
        end_date_text,
        category,
        start_date,
        end_date
    """

    start_date_text = (
        request.args.get(
            "start_date",
            "",
            type=str
        )
        .strip()
    )

    end_date_text = (
        request.args.get(
            "end_date",
            "",
            type=str
        )
        .strip()
    )

    category = (
        request.args.get(
            "category",
            "",
            type=str
        )
        .strip()
    )

    # ------------------------------------------------------
    # Parse start date
    # ------------------------------------------------------

    start = None

    if start_date_text:

        try:

            start = datetime.strptime(
                start_date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            raise ValueError(
                "Invalid start date. "
                "Please use YYYY-MM-DD."
            )

    # ------------------------------------------------------
    # Parse end date
    # ------------------------------------------------------

    end = None

    if end_date_text:

        try:

            end = datetime.strptime(
                end_date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            raise ValueError(
                "Invalid end date. "
                "Please use YYYY-MM-DD."
            )

    # ------------------------------------------------------
    # Validate date range
    # ------------------------------------------------------

    if start and end and start > end:

        raise ValueError(
            "The 'From' date cannot be later "
            "than the 'To' date."
        )

    return (
        start_date_text,
        end_date_text,
        category,
        start,
        end,
    )


# ==========================================================
# REPORT DATA
# ==========================================================

def _report_data():

    (
        start_date_text,
        end_date_text,
        category,
        start,
        end,
    ) = _filters()

    data = ReportService.report_data(
        user_id=current_user.id,
        start_date=start,
        end_date=end,
        category=category or None,
    )

    return (
        data,
        start_date_text,
        end_date_text,
        category,
    )


# ==========================================================
# REPORT INDEX
# ==========================================================

@reports_bp.route("/")
@login_required
def index():

    try:

        (
            data,
            start_date,
            end_date,
            category,
        ) = _report_data()

    except ValueError as exc:

        flash(
            str(exc),
            "warning"
        )

        return redirect(
            url_for(
                "reports.index"
            )
        )

    return render_template(
        "reports/index.html",

        # --------------------------------------------------
        # Summary
        # --------------------------------------------------

        summary=data["summary"],

        # --------------------------------------------------
        # Income categories
        # --------------------------------------------------

        income_labels=(
            data[
                "income_categories"
            ]["labels"]
        ),

        income_values=(
            data[
                "income_categories"
            ]["values"]
        ),

        # --------------------------------------------------
        # Expense categories
        # --------------------------------------------------

        expense_labels=(
            data[
                "expense_categories"
            ]["labels"]
        ),

        expense_values=(
            data[
                "expense_categories"
            ]["values"]
        ),

        # --------------------------------------------------
        # Monthly trend
        # --------------------------------------------------

        months=(
            data[
                "monthly_trend"
            ]["labels"]
        ),

        monthly_income=(
            data[
                "monthly_trend"
            ]["income"]
        ),

        monthly_expenses=(
            data[
                "monthly_trend"
            ]["expenses"]
        ),

        # --------------------------------------------------
        # Available categories
        # --------------------------------------------------

        categories=ReportService.categories(
            current_user.id
        ),

        # --------------------------------------------------
        # Current filters
        # --------------------------------------------------

        start_date=start_date,
        end_date=end_date,
        category=category,

        # --------------------------------------------------
        # Complete report payload
        # Useful for future report widgets
        # --------------------------------------------------

        report=data,
    )


# ==========================================================
# PDF EXPORT
# ==========================================================

@reports_bp.route("/export/pdf")
@login_required
def export_pdf():

    try:

        (
            data,
            start_date,
            end_date,
            category,
        ) = _report_data()

    except ValueError as exc:

        flash(
            str(exc),
            "warning"
        )

        return redirect(
            url_for(
                "reports.index"
            )
        )

    pdf = ExportService.pdf(
        data,
        start_date,
        end_date,
        category,
    )

    filename = (
        f"focost_financial_report_"
        f"{datetime.now():%Y%m%d_%H%M}.pdf"
    )

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


# ==========================================================
# EXCEL EXPORT
# ==========================================================

@reports_bp.route("/export/excel")
@login_required
def export_excel():

    try:

        (
            data,
            start_date,
            end_date,
            category,
        ) = _report_data()

    except ValueError as exc:

        flash(
            str(exc),
            "warning"
        )

        return redirect(
            url_for(
                "reports.index"
            )
        )

    excel = ExportService.excel(
        data,
        start_date,
        end_date,
        category,
    )

    filename = (
        f"focost_financial_report_"
        f"{datetime.now():%Y%m%d_%H%M}.xlsx"
    )

    return send_file(
        excel,
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        as_attachment=True,
        download_name=filename,
    )


# ==========================================================
# TRANSACTIONS
# ==========================================================

@reports_bp.route("/transactions")
@login_required
def transactions():

    try:

        (
            data,
            start_date,
            end_date,
            category,
        ) = _report_data()

    except ValueError as exc:

        flash(
            str(exc),
            "warning"
        )

        return redirect(
            url_for(
                "reports.index"
            )
        )

    transactions = []

    # ------------------------------------------------------
    # Income transactions
    # ------------------------------------------------------

    for item in data[
        "summary"
    ].get(
        "income_records",
        []
    ):

        transactions.append({

            "type": "Income",

            "date": item.received_date,

            "category": item.category,

            "description": item.source,

            "amount": item.amount,

        })

    # ------------------------------------------------------
    # Expense transactions
    # ------------------------------------------------------

    for item in data[
        "summary"
    ].get(
        "expense_records",
        []
    ):

        transactions.append({

            "type": "Expense",

            "date": item.expense_date,

            "category": item.category,

            "description": item.merchant,

            "amount": item.amount,

        })

    # ------------------------------------------------------
    # Latest first
    # ------------------------------------------------------

    transactions.sort(
        key=lambda x: x["date"],
        reverse=True,
    )

    return render_template(
        "reports/transactions.html",

        transactions=transactions,

        start_date=start_date,

        end_date=end_date,

        category=category,
    )