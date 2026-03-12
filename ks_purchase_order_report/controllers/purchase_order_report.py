# -*- coding: utf-8 -*-
# Report source: doc/REPORT_SOURCE_PU001.md — Row 3 = description, Row 4 = column name, data from Row 5.

import io
from odoo import http, _
from odoo.http import content_disposition, request
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter

from ..models.report_source_pu001 import (
    PU001_ROW3_DESCRIPTIONS,
    PU001_ROW4_HEADERS,
    PU001_FIELD_NAMES,
)
COLUMN_WIDTHS = [18, 25, 22, 32, 10, 12, 15, 15, 15, 15, 12, 12, 12, 12, 12, 15, 18]


def _make_workbook_formats(workbook):
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#FFFF00',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'underline': True,
    })
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter',
    })
    number_format = workbook.add_format({
        'border': 1,
        'align': 'right',
        'valign': 'vcenter',
        'num_format': '#,##0.00',
    })
    return header_format, cell_format, number_format


def _write_report_lines_to_worksheet(worksheet, report_lines, header_format, cell_format, number_format):
    """Write Row 3 (description), Row 4 (column names), then data from Row 5 (PU-001)."""
    # Row 3 (0-based 2): description/calculation
    for col_num, desc in enumerate(PU001_ROW3_DESCRIPTIONS):
        worksheet.write(2, col_num, desc, cell_format)
    # Row 4 (0-based 3): column names (header row)
    for col_num, header in enumerate(PU001_ROW4_HEADERS):
        worksheet.write(3, col_num, header, header_format)
    # Data from Row 5 (0-based 4+)
    numeric_fields = {
        'qty', 'fob', 'amount', 'payment', 'balance', 'inr_amount',
        'freight_ins', 'bcd', 'sws', 'igst', 'fine_interest', 'total_exp', 'per_pc_landed_cost',
    }
    for row_idx, line in enumerate(report_lines):
        excel_row = 4 + row_idx
        for col_num, fname in enumerate(PU001_FIELD_NAMES):
            if fname == 'order_id':
                value = line.order_id.name if line.order_id else ''
                worksheet.write(excel_row, col_num, value, cell_format)
            else:
                value = getattr(line, fname, None)
                if fname in numeric_fields:
                    worksheet.write(excel_row, col_num, value or 0.0, number_format)
                else:
                    worksheet.write(excel_row, col_num, value or '', cell_format)


class PurchaseOrderReportController(http.Controller):

    @http.route('/purchase_order/export_otek_xlsx', type='http', auth='user', methods=['GET', 'POST'])
    def export_otek_purchase_order_xlsx(self, **kwargs):
        """
        Export to Excel:
        - If line_ids is provided: export those ks.purchase.order.otek.report.line records.
        - Otherwise: legacy behaviour – all Otek POL (no date filter).
        """
        if not xlsxwriter:
            raise UserError(_("xlsxwriter is required for Excel export. Please install it: pip install xlsxwriter"))

        line_ids_param = kwargs.get('line_ids')
        if line_ids_param:
            try:
                ids = [int(x.strip()) for x in str(line_ids_param).split(',') if x.strip()]
            except (ValueError, TypeError):
                ids = []
            if ids:
                report_lines = request.env['ks.purchase.order.otek.report.line'].browse(ids).exists()
                if report_lines:
                    return self._export_report_lines_xlsx(report_lines)
            # Fall through to legacy if no valid report lines

        # Legacy: all Otek purchase order lines (no date filter)
        brand = request.env['product.brand'].search([('name', '=ilike', 'otek')], limit=1)
        if not brand:
            raise UserError(_("Brand 'otek' not found. Please create the brand first."))

        pol_domain = [
            ('product_id.product_tmpl_id.brand_id', '=', brand.id),
            ('display_type', '=', False),
        ]
        pol_lines = request.env['purchase.order.line'].search(pol_domain)
        if not pol_lines:
            raise UserError(_("No purchase order lines found with Otek brand products."))

        return self._export_pol_lines_xlsx(pol_lines)

    def _export_report_lines_xlsx(self, report_lines):
        """Generate Excel from report lines (PU-001: Row 3=description, Row 4=headers, data from Row 5)."""
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Otek Purchase Order Report')
        header_format, cell_format, number_format = _make_workbook_formats(workbook)
        for col_num, width in enumerate(COLUMN_WIDTHS):
            worksheet.set_column(col_num, col_num, width)
        _write_report_lines_to_worksheet(
            worksheet, report_lines, header_format, cell_format, number_format
        )
        workbook.close()
        output.seek(0)
        filename = 'Otek_Purchase_Order_Report.xlsx'
        response = request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )
        output.close()
        return response

    def _export_pol_lines_xlsx(self, pol_lines):
        """Generate Excel from purchase.order.line recordset (legacy). PU-001: Row 3=desc, Row 4=headers, data from Row 5."""
        from ..models.purchase_order_otek_report import _get_line_igst

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Otek Purchase Order Report')
        header_format, cell_format, number_format = _make_workbook_formats(workbook)
        for col_num, width in enumerate(COLUMN_WIDTHS):
            worksheet.set_column(col_num, col_num, width)
        for col_num, desc in enumerate(PU001_ROW3_DESCRIPTIONS):
            worksheet.write(2, col_num, desc, cell_format)
        for col_num, header in enumerate(PU001_ROW4_HEADERS):
            worksheet.write(3, col_num, header, header_format)

        row_num = 4
        for line in pol_lines:
            order = line.order_id
            product = line.product_id
            product_template = product.product_tmpl_id
            qty = line.product_qty or 0.0
            rate = order.fob or 0.0
            price_unit = line.price_unit or 0.0
            fob = rate * price_unit
            amount = rate * qty if rate else 0.0
            payment = order.advance_payment or 0.0
            balance = amount - payment
            conversion_rate = order.conversion_rate or 1.0
            inr_amount = conversion_rate * amount
            igst = _get_line_igst(line)
            total_exp = igst
            per_pc_landed_cost = (total_exp + inr_amount) / qty if qty else 0.0

            worksheet.write(row_num, 0, order.name or '', cell_format)
            worksheet.write(row_num, 1, order.partner_id.name if order.partner_id else '', cell_format)
            worksheet.write(row_num, 2, product_template.categ_id.name if product_template.categ_id else '', cell_format)
            worksheet.write(row_num, 3, product_template.name or product.name or '', cell_format)
            worksheet.write(row_num, 4, qty, number_format)
            worksheet.write(row_num, 5, fob, number_format)
            worksheet.write(row_num, 6, amount, number_format)
            worksheet.write(row_num, 7, payment, number_format)
            worksheet.write(row_num, 8, balance, number_format)
            worksheet.write(row_num, 9, inr_amount, number_format)
            worksheet.write(row_num, 10, 0.0, number_format)
            worksheet.write(row_num, 11, 0.0, number_format)
            worksheet.write(row_num, 12, 0.0, number_format)
            worksheet.write(row_num, 13, igst, number_format)
            worksheet.write(row_num, 14, 0.0, number_format)
            worksheet.write(row_num, 15, total_exp, number_format)
            worksheet.write(row_num, 16, per_pc_landed_cost, number_format)
            row_num += 1

        workbook.close()
        output.seek(0)
        filename = 'Otek_Purchase_Order_Report.xlsx'
        response = request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )
        output.close()
        return response
