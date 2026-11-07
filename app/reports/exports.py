from io import BytesIO
from datetime import datetime
from app.utils.timezone import now
from pathlib import Path
import os
import tempfile

from flask import current_app
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image as RLImage,
)


class ExportService:
    """Generate consistent branded, locale-aware financial report exports."""

    LABEL_KEYS = {
        "FOCOST — FINANCIAL REPORT": "report_title", "Generated": "generated",
        "Period": "period", "Category": "category", "All time": "all_time",
        "Present": "present", "All Categories": "all_categories",
        "CURRENT FINANCIAL POSITION": "current_financial_position",
        "Total cash income": "total_cash_income", "Less: total cash expenses": "less_cash_expenses",
        "Available / savings balance": "available_savings_balance",
        "Add: cumulative goal contributions": "cumulative_goal_contributions",
        "Add: current investment value": "current_investment_value",
        "Estimated net worth": "estimated_net_worth", "Note": "note",
        "Period Total Income": "period_total_income", "Period Total Expenses": "period_total_expenses",
        "Period Net Savings": "period_net_savings", "Period Savings Rate (%)": "period_savings_rate",
        "Transactions": "transactions", "Income by Category": "income_by_category",
        "Expense by Category": "expense_by_category", "Report Summary": "report_summary",
        "Financial Position": "financial_position",
        "FOCOST — STATEMENT OF FINANCIAL POSITION": "statement_financial_position",
        "Current position": "current_position", "Component": "component", "Amount": "amount",
        "Accounting context": "accounting_context", "Transaction Detail": "transaction_detail",
        "Type": "type", "Date": "date", "Source / Merchant": "source_merchant",
        "Original Amount": "original_amount", "Original Currency": "original_currency",
        "Display Amount": "converted_amount", "Recurring": "recurring", "Notes": "notes",
        "Savings Rate": "savings_rate_label", "Yes": "yes", "No": "no",
        "Income": "income", "Expense": "expense", "No data": "no_data",
    }

    @staticmethod
    def _t(language_code, key):
        from app.services.language_service import LanguageService
        return LanguageService.translate(language_code or "en", key)

    @staticmethod
    def _label(text, language_code="en"):
        key = ExportService.LABEL_KEYS.get(text)
        return ExportService._t(language_code, key) if key else text

    @staticmethod
    def _money(value, currency="NGN"):
        from app.services.currency_service import CurrencyService
        return CurrencyService.format(value, currency, include_code=True)

    @staticmethod
    def _logo_path():
        return Path(current_app.root_path) / "static" / "images" / "focost_logo.png"

    @staticmethod
    def _faded_logo():
        """Return an in-memory low-opacity copy of the existing FOCOST logo."""
        from PIL import Image

        logo_path = ExportService._logo_path()
        image = Image.open(logo_path).convert("RGBA")
        alpha = image.getchannel("A").point(lambda value: int(value * 0.08))
        image.putalpha(alpha)
        return image

    @staticmethod
    def _financial_position_rows(position, language_code="en"):
        return [
            (ExportService._label("Total cash income", language_code), position["cash_income"]),
            (ExportService._label("Less: total cash expenses", language_code), -position["cash_expenses"]),
            (ExportService._label("Available / savings balance", language_code), position["available_balance"]),
            (ExportService._label("Add: cumulative goal contributions", language_code), position["goal_contributions"]),
            (ExportService._label("Add: current investment value", language_code), position["investment_current_value"]),
            (ExportService._label("Estimated net worth", language_code), position["net_worth"]),
        ]

    @staticmethod
    def _excel_watermark_path():
        """Create a temporary faded copy of the existing logo for Excel output."""
        faded = ExportService._faded_logo()
        handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        path = handle.name
        handle.close()
        faded.save(path, format="PNG")
        return path

    @staticmethod
    def _configure_excel_sheet(ws, logo_path=None, language_code="en"):
        ws.sheet_view.showGridLines = False
        ws.oddHeader.center.text = '&B' + ExportService._label('FOCOST — FINANCIAL REPORT', language_code)
        ws.oddHeader.center.size = 10
        ws.oddHeader.center.font = 'Calibri,Bold'
        ws.oddHeader.center.color = '1F4E78'
        ws.oddFooter.left.text = 'FOCOST'
        ws.oddFooter.right.text = 'Page &[Page] of &[Pages]'
        ws.oddFooter.left.font = 'Calibri,Italic'
        ws.oddFooter.right.font = 'Calibri'
        ws.oddFooter.left.size = 8
        ws.oddFooter.right.size = 8

        if logo_path:
            try:
                image = XLImage(logo_path)
                image.width = 80
                image.height = 80
                ws.add_image(image, "H2")
            except Exception:
                # Header/footer branding remains available even if the optional
                # worksheet image embedding is unavailable in a runtime.
                pass

    @staticmethod
    def excel(data, start_date=None, end_date=None, category=None, language_code="en"):
        wb = Workbook()
        excel_logo_path = None
        try:
            excel_logo_path = ExportService._excel_watermark_path()
        except Exception:
            excel_logo_path = None

        ws = wb.active
        ws.title = ExportService._label("Report Summary", language_code)[:31]
        ExportService._configure_excel_sheet(ws, excel_logo_path, language_code)

        ws["A1"] = ExportService._label("FOCOST — FINANCIAL REPORT", language_code)
        ws["A1"].font = Font(size=18, bold=True, color="1F4E78")
        ws.merge_cells("A1:F1")
        ws["A2"] = ExportService._label("Generated", language_code)
        ws["B2"] = now().strftime("%d %b %Y %H:%M")
        ws["A3"] = ExportService._label("Period", language_code)
        ws["B3"] = f"{start_date or ExportService._label('All time', language_code)} – {end_date or ExportService._label('Present', language_code)}"
        ws["A4"] = ExportService._label("Category", language_code)
        ws["B4"] = category or ExportService._label("All Categories", language_code)

        summary = data["summary"]
        position = data["financial_position"]
        display_currency = data.get("display_currency", "NGN")

        rows = [
            (ExportService._label("Period Total Income", language_code), summary["income"]),
            (ExportService._label("Period Total Expenses", language_code), summary["expenses"]),
            (ExportService._label("Period Net Savings", language_code), summary["savings"]),
            (ExportService._label("Period Savings Rate (%)", language_code), summary["savings_rate"]),
            (ExportService._label("Transactions", language_code), summary["transactions"]),
        ]
        for r, (label, value) in enumerate(rows, 6):
            ws.cell(r, 1, label).font = Font(bold=True)
            ws.cell(r, 2, value)
            if r != 9 and r != 10:
                ws.cell(r, 2).number_format = '#,##0.00'

        # Current financial position statement. This is deliberately separate
        # from period-performance totals and uses DashboardService's authoritative
        # current balances so filters cannot distort net worth.
        start_row = 13
        ws.cell(start_row, 1, ExportService._label("CURRENT FINANCIAL POSITION", language_code)).font = Font(size=13, bold=True, color="1F4E78")
        ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=2)
        for offset, (label, value) in enumerate(ExportService._financial_position_rows(position, language_code), 1):
            row = start_row + offset
            is_emphasis = offset in {3, 6}
            ws.cell(row, 1, label).font = Font(bold=is_emphasis)
            ws.cell(row, 2, value)
            ws.cell(row, 2).number_format = '#,##0.00'
            if offset == 6:
                ws.cell(row, 1).font = Font(bold=True, color="1F4E78")
                ws.cell(row, 2).font = Font(bold=True, color="1F4E78")

        ws.cell(start_row + 7, 1, ExportService._label("Note", language_code)).font = Font(bold=True)
        ws.cell(start_row + 7, 2, ExportService._t(language_code, "financial_position_note"))
        ws.cell(start_row + 7, 2).alignment = Alignment(wrap_text=True, vertical="top")

        for col, width in {1: 34, 2: 24, 3: 18, 4: 18, 5: 18, 6: 18}.items():
            ws.column_dimensions[get_column_letter(col)].width = width

        # Category sheets
        for title, key in (("Income by Category", "income_categories"), ("Expense by Category", "expense_categories")):
            translated_title = ExportService._label(title, language_code)
            sh = wb.create_sheet(translated_title[:31])
            ExportService._configure_excel_sheet(sh, excel_logo_path, language_code)
            sh.append([ExportService._label("Category", language_code), ExportService._label("Amount", language_code)])
            for cell in sh[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E78")
            for label, value in zip(data[key]["labels"], data[key]["values"]):
                sh.append([label, value])
            sh.column_dimensions["A"].width = 32
            sh.column_dimensions["B"].width = 20
            for row in sh.iter_rows(min_row=2, min_col=2, max_col=2):
                row[0].number_format = '#,##0.00'

        # Transactions
        sh = wb.create_sheet(ExportService._label("Transactions", language_code)[:31])
        ExportService._configure_excel_sheet(sh, excel_logo_path, language_code)
        sh.append([ExportService._label("Type", language_code), ExportService._label("Date", language_code), ExportService._label("Category", language_code), ExportService._label("Source / Merchant", language_code), ExportService._label("Original Amount", language_code), ExportService._label("Original Currency", language_code), f"{ExportService._label('Display Amount', language_code)} ({display_currency})", ExportService._label("Recurring", language_code), ExportService._label("Notes", language_code)])
        for cell in sh[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
        from app.services.financial_currency_service import FinancialCurrencyService
        for item in data["summary"]["income_records"]:
            converted = FinancialCurrencyService.convert_record(item, display_currency, date_field="received_date")
            sh.append([ExportService._label("Income", language_code), item.received_date, item.category, item.source, float(item.amount or 0), item.currency or "NGN", float(converted), ExportService._label("Yes" if item.recurring else "No", language_code), item.notes or ""])
        for item in data["summary"]["expense_records"]:
            converted = FinancialCurrencyService.convert_record(item, display_currency, date_field="expense_date")
            sh.append([ExportService._label("Expense", language_code), item.expense_date, item.category, item.merchant, float(item.amount or 0), item.currency or "NGN", float(converted), ExportService._label("Yes" if item.recurring else "No", language_code), item.notes or ""])
        widths = [12, 15, 24, 30, 18, 18, 22, 12, 40]
        for i, width in enumerate(widths, 1):
            sh.column_dimensions[get_column_letter(i)].width = width
        for row in sh.iter_rows(min_row=2):
            row[1].number_format = "dd mmm yyyy"
            row[4].number_format = '#,##0.00'
            row[6].number_format = '#,##0.00'

        # Financial position sheet for a clean printable statement.
        sh = wb.create_sheet(ExportService._label("Financial Position", language_code)[:31])
        ExportService._configure_excel_sheet(sh, excel_logo_path, language_code)
        sh["A1"] = ExportService._label("FOCOST — STATEMENT OF FINANCIAL POSITION", language_code)
        sh["A1"].font = Font(size=16, bold=True, color="1F4E78")
        sh.merge_cells("A1:B1")
        sh["A2"] = ExportService._label("Current position", language_code)
        sh["B2"] = now().strftime("%d %b %Y")
        sh["A4"] = ExportService._label("Component", language_code)
        sh["B4"] = f"{ExportService._label('Amount', language_code)} ({display_currency})"
        for cell in sh[4]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
        for row_index, (label, value) in enumerate(ExportService._financial_position_rows(position, language_code), 5):
            sh.cell(row_index, 1, label)
            sh.cell(row_index, 2, value)
            sh.cell(row_index, 2).number_format = '#,##0.00'
            if row_index in {7, 10}:
                sh.cell(row_index, 1).font = Font(bold=True)
                sh.cell(row_index, 2).font = Font(bold=True)
        sh["A12"] = ExportService._label("Accounting context", language_code)
        sh["A12"].font = Font(bold=True)
        sh["A13"] = ExportService._t(language_code, "financial_position_explanation")
        sh.merge_cells("A13:B15")
        sh["A13"].alignment = Alignment(wrap_text=True, vertical="top")
        sh.column_dimensions["A"].width = 72
        sh.column_dimensions["B"].width = 24
        for r in range(13, 16):
            sh.cell(r, 1).alignment = Alignment(wrap_text=True)

        out = BytesIO()
        try:
            wb.save(out)
        finally:
            if excel_logo_path:
                try:
                    os.unlink(excel_logo_path)
                except OSError:
                    pass
        out.seek(0)
        return out

    @staticmethod
    def _pdf_watermark(canvas, doc):
        """
        Draw a subtle FOCOST brand watermark on every PDF page.

        The watermark is intentionally rendered before the report content
        so that all report text/tables remain visually above it.
        """
        canvas.saveState()

        try:
            page_width, page_height = A4

            logo = ImageReader(ExportService._logo_path())

            # Large, subtle centered brand watermark.
            logo_size = 245
            logo_x = (page_width - logo_size) / 2
            logo_y = (page_height - logo_size) / 2 + 5

            canvas.setFillAlpha(0.055)

            canvas.drawImage(
                logo,
                logo_x,
                logo_y,
                width=logo_size,
                height=logo_size,
                preserveAspectRatio=True,
                mask="auto",
            )

            # Very subtle FOCOST wordmark beneath the logo.
            canvas.setFont("Helvetica-Bold", 30)
            canvas.setFillColor(colors.HexColor("#1f4e78"))
            canvas.setFillAlpha(0.035)

            canvas.drawCentredString(
                page_width / 2,
                logo_y - 24,
                "FOCOST",
            )

        except Exception:
            # Branding must never prevent a financial report from exporting.
            pass

        finally:
            canvas.restoreState()

    @staticmethod
    def _pdf_header(canvas, doc):
        canvas.saveState()
        try:
            logo = ImageReader(ExportService._logo_path())
            canvas.drawImage(logo, 28, A4[1] - 55, width=34, height=34, preserveAspectRatio=True, mask="auto")
            canvas.setFont("Helvetica-Bold", 9)
            canvas.setFillColor(colors.HexColor("#1f4e78"))
            canvas.drawString(68, A4[1] - 42, "FOCOST")
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.grey)
            canvas.drawRightString(A4[0] - 28, 18, f"Page {doc.page}")
        except Exception:
            pass
        finally:
            canvas.restoreState()

    @staticmethod
    def _pdf_page(canvas, doc):
        ExportService._pdf_watermark(canvas, doc)
        ExportService._pdf_header(canvas, doc)

    @staticmethod
    def pdf(data, start_date=None, end_date=None, category=None, language_code="en"):
        out = BytesIO()
        doc = SimpleDocTemplate(
            out,
            pagesize=A4,
            rightMargin=28,
            leftMargin=28,
            topMargin=72,
            bottomMargin=32,
        )
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="RightSmall", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=8))
        styles.add(ParagraphStyle(name="StatementLabel", parent=styles["Normal"], fontSize=9))
        styles.add(ParagraphStyle(name="StatementValue", parent=styles["Normal"], fontSize=9, alignment=TA_RIGHT))

        summary = data["summary"]
        position = data["financial_position"]
        display_currency = data.get("display_currency", "NGN")
        story = [
            Paragraph(ExportService._label("FOCOST — FINANCIAL REPORT", language_code), styles["Title"]),
            Paragraph(
                f"{ExportService._label('Generated', language_code)}: {now().strftime('%d %b %Y %H:%M')} &nbsp; | &nbsp; "
                f"{ExportService._label('Period', language_code)}: {start_date or ExportService._label('All time', language_code)} – {end_date or ExportService._label('Present', language_code)} &nbsp; | &nbsp; "
                f"{ExportService._label('Category', language_code)}: {category or ExportService._label('All Categories', language_code)}",
                styles["Normal"],
            ),
            Spacer(1, 12),
        ]

        # Financial position statement: current balances are sourced from
        # DashboardService and are independent of period/category filters.
        story.append(Paragraph(ExportService._label("Financial Position", language_code), styles["Heading2"]))
        position_table = [[ExportService._label("Component", language_code), ExportService._label("Amount", language_code)]]
        for label, value in ExportService._financial_position_rows(position, language_code):
            position_table.append([label, ExportService._money(value, display_currency)])
        pt = Table(position_table, colWidths=[370, 169], repeatRows=1)
        pt.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), .25, colors.lightgrey),
            ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
            ("FONTNAME", (0, 6), (-1, 6), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 6), (-1, 6), colors.HexColor("#1f4e78")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story += [pt, Spacer(1, 8)]
        story.append(Paragraph(
            ExportService._t(language_code, "financial_position_explanation"),
            styles["Normal"],
        ))
        story.append(Spacer(1, 16))

        kpis = [
            [ExportService._label("Period Total Income", language_code), ExportService._label("Period Total Expenses", language_code), ExportService._label("Period Net Savings", language_code), ExportService._label("Savings Rate", language_code), ExportService._label("Transactions", language_code)],
            [ExportService._money(summary["income"], display_currency), ExportService._money(summary["expenses"], display_currency), ExportService._money(summary["savings"], display_currency), f"{summary['savings_rate']:.1f}%", str(summary["transactions"])],
        ]
        t = Table(kpis, colWidths=[107.8] * 5)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), .5, colors.grey),
            ("INNERGRID", (0, 0), (-1, -1), .25, colors.lightgrey),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story += [t, Spacer(1, 18)]

        for title, key in (("Income by Category", "income_categories"), ("Expense by Category", "expense_categories")):
            table_data = [[ExportService._label("Category", language_code), ExportService._label("Amount", language_code)]] + [[str(a), ExportService._money(b, display_currency)] for a, b in zip(data[key]["labels"], data[key]["values"])]
            if len(table_data) == 1:
                table_data.append([ExportService._label("No data", language_code), ExportService._money(0, display_currency)])
            table = Table(table_data, colWidths=[300, 239], repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), .25, colors.lightgrey),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story += [Paragraph(ExportService._label(title, language_code), styles["Heading2"]), table, Spacer(1, 14)]

        story.append(PageBreak())
        story.append(Paragraph(ExportService._label("Transaction Detail", language_code), styles["Heading1"]))
        tx = [[ExportService._label("Type", language_code), ExportService._label("Date", language_code), ExportService._label("Category", language_code), ExportService._label("Source / Merchant", language_code), ExportService._label("Amount", language_code)]]

        # Build one unified transaction stream before rendering.
        # Income and Expense must be ordered strictly by transaction date/time,
        # regardless of transaction type. The transaction's recorded
        # created_at timestamp is used as the time component when two
        # transactions share the same financial date. ID is the final stable
        # tie-breaker.
        transaction_rows = []
        from app.services.financial_currency_service import FinancialCurrencyService

        for item in summary["income_records"]:
            transaction_rows.append({
                "type": ExportService._label("Income", language_code),
                "date": item.received_date,
                "created_at": getattr(item, "created_at", None),
                "id": item.id,
                "category": str(item.category or "Uncategorized"),
                "description": str(item.source or ""),
                "amount": FinancialCurrencyService.convert_record(item, display_currency, date_field="received_date"),
                "original_currency": item.currency or "NGN",
            })

        for item in summary["expense_records"]:
            transaction_rows.append({
                "type": ExportService._label("Expense", language_code),
                "date": item.expense_date,
                "created_at": getattr(item, "created_at", None),
                "id": item.id,
                "category": str(item.category or "Uncategorized"),
                "description": str(item.merchant or ""),
                "amount": FinancialCurrencyService.convert_record(item, display_currency, date_field="expense_date"),
                "original_currency": item.currency or "NGN",
            })

        # Chronological order is independent of Income/Expense type.
        # Use the financial transaction date first, then the recorded creation
        # timestamp for same-date transactions, then the database ID for a
        # deterministic final order.
        transaction_rows.sort(
            key=lambda row: (
                row["date"],
                row["created_at"] or datetime.min,
                row["id"],
            )
        )

        for row in transaction_rows:
            tx.append([
                row["type"],
                row["date"].strftime("%d %b %Y"),
                row["category"],
                f"{row['description']} (original: {row['original_currency']})",
                ExportService._money(row["amount"], display_currency),
            ])
        if len(tx) == 1:
            tx.append(["—", "—", ExportService._label("No data", language_code), "—", ExportService._money(0, display_currency)])
        table = Table(tx, colWidths=[55, 75, 105, 185, 119], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e78")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), .25, colors.lightgrey),
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ]))
        story.append(table)

        doc.build(story, onFirstPage=ExportService._pdf_page, onLaterPages=ExportService._pdf_page)
        out.seek(0)
        return out
