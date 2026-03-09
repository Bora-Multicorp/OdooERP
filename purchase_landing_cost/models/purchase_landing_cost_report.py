# -*- coding: utf-8 -*-

import io
import base64
from odoo import api, fields, models, _
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class PurchaseLandingCostReport(models.TransientModel):
    _name = "purchase.landing.cost.report"
    _description = "Net Landing Cost Report per PO"

    purchase_order_id = fields.Many2one(
        "purchase.order",
        string="Purchase Order",
        required=True,
        readonly=True,
        ondelete="cascade",
    )
    misc = fields.Float(string="Misc", digits="Product Price", default=0.0)
    freight = fields.Float(string="Freight", digits="Product Price", default=0.0)
    insurance = fields.Float(string="Insurance", digits="Product Price", default=0.0)
    foc_freight = fields.Float(string="Freight (FOC)", digits="Product Price", default=0.0)
    foc_insurance = fields.Float(string="Insurance (FOC)", digits="Product Price", default=0.0)
    bcd_percent = fields.Float(string="BCD %", default=0.0, digits="Product Price")
    sws_percent = fields.Float(string="SWS %", default=10.0, digits="Product Price")
    gst_percent = fields.Float(string="GST %", default=18.0, digits="Product Price")

    line_ids = fields.One2many(
        "purchase.landing.cost.report.line",
        "report_id",
        string="Lines",
        copy=False,
    )
    standard_line_ids = fields.One2many(
        "purchase.landing.cost.report.line",
        "report_id",
        string="Standard Items",
        compute="_compute_standard_foc_lines",
        inverse="_inverse_standard_line_ids",
        copy=False,
    )
    foc_line_ids = fields.One2many(
        "purchase.landing.cost.report.line",
        "report_id",
        string="Free of Cost",
        compute="_compute_standard_foc_lines",
        inverse="_inverse_foc_line_ids",
        copy=False,
    )

    def _compute_standard_foc_lines(self):
        for report in self:
            report.standard_line_ids = report.line_ids.filtered(lambda l: not l.is_foc)
            report.foc_line_ids = report.line_ids.filtered(lambda l: l.is_foc)

    def _inverse_standard_line_ids(self):
        pass

    def _inverse_foc_line_ids(self):
        pass

    def _fill_lines_from_po(self):
        self.ensure_one()
        order = self.purchase_order_id
        if not order or not order.order_line:
            return
        lines_vals = []
        for seq, line in enumerate(
            order.order_line.filtered(lambda l: l.display_type not in ("line_section", "line_note") and l.product_id),
            1,
        ):
            product = line.product_id
            # FOC comes from product.template (is_foc); line has product_id -> product.product -> product_tmpl_id
            is_foc = getattr(product.product_tmpl_id, "is_foc", False)
            price = line.price_unit
            qty = line.product_qty
            lines_vals.append({
                "sequence": seq,
                "purchase_order_line_id": line.id,
                "product_id": product.id,
                "is_foc": is_foc,
                "hsn_code": getattr(product, "l10n_in_hsn_code", None) or "",
                "usd_rate": price,
                "qty": qty,
                "usd_value": price * qty,
                "exchange_rate": 1.0,
            })
        self.line_ids = [(0, 0, v) for v in lines_vals]

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref("purchase_landing_cost.action_report_purchase_landing_cost").report_action(self)

    def _generate_xlsx(self):
        """Generate Excel workbook in PU-003 format: header, Standard Items section, FOC section, totals and grand total."""
        self.ensure_one()
        if xlsxwriter is None:
            raise UserError(_("Please install xlsxwriter: pip install xlsxwriter"))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Net Landing Cost")
        # Column widths to match screenshot
        widths = [8, 36, 12, 14, 12, 16, 12, 18, 14, 14, 14, 18, 12, 14, 14, 14, 10, 10, 10]
        for i, w in enumerate(widths):
            sheet.set_column(i, i, w)

        header_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAD3", "border": 1, "text_wrap": True})
        num_fmt = workbook.add_format({"border": 1, "num_format": "#,##0.00", "align": "right"})
        num_fmt_pct = workbook.add_format({"border": 1, "num_format": "0.00", "align": "right"})
        total_fmt = workbook.add_format({"bold": True, "border": 1, "num_format": "#,##0.00", "align": "right", "bg_color": "#FFF2CC"})
        total_label_fmt = workbook.add_format({"bold": True, "border": 1, "bg_color": "#FFF2CC"})
        cell_fmt = workbook.add_format({"border": 1, "valign": "vcenter"})
        title_fmt = workbook.add_format({"bold": True, "font_size": 12})

        row = 0
        # Title
        sheet.merge_range(row, 0, row, len(widths) - 1, "This is a report calculating Net Landing Cost of each product per PO", title_fmt)
        row += 2

        order = self.purchase_order_id
        partner_name = order.partner_id.name if order and order.partner_id else ""
        po_name = order.name if order else ""

        # Global inputs (top right) - row 1-4
        sheet.write(1, 14, "Exchange Rate", cell_fmt)
        sheet.write(2, 14, "Misc", cell_fmt)
        sheet.write(3, 14, "Freight", cell_fmt)
        sheet.write(4, 14, "Insurance", cell_fmt)
        # Values from report (first line exchange rate; report misc/freight/insurance)
        first_line = self.line_ids[:1]
        ex_rate = first_line.exchange_rate if first_line else 1.0
        sheet.write(1, 15, ex_rate, num_fmt)
        sheet.write(2, 15, self.misc or 0, num_fmt)
        sheet.write(3, 15, self.freight or 0, num_fmt)
        sheet.write(4, 15, self.insurance or 0, num_fmt)

        col_headers = [
            "Sr No", "Stock Item", "From PO HSN", "From PO USD Rate", "From PO Qty", "From PO USD Value",
            "Exchange Rate", "As per Formula INR Value", "As per Formula Misc", "As per Formula Freight", "As per Formula Insurance",
            "As per Formula Assessable Value", "BCD", "SWS @ 10%", "IGST @ 18", "Total Duty",
            "SWS %", "BCD %", "GST %",
        ]
        num_cols = len(col_headers)

        def write_section(lines, section_title, po_label, start_row, skip_section_header=False):
            r = start_row
            if not skip_section_header:
                sheet.write(r, 0, partner_name, cell_fmt)
                r += 1
                sheet.write(r, 0, po_label, cell_fmt)
                r += 2
            for c, h in enumerate(col_headers):
                sheet.write(r, c, h, header_fmt)
            r += 1
            data_start = r
            for line in lines:
                sheet.write(r, 0, line.sequence or 0, cell_fmt)
                sheet.write(r, 1, line.product_id.display_name or "", cell_fmt)
                sheet.write(r, 2, line.hsn_code or "", cell_fmt)
                sheet.write(r, 3, line.usd_rate or 0, num_fmt)
                sheet.write(r, 4, line.qty or 0, num_fmt)
                sheet.write(r, 5, line.usd_value or 0, num_fmt)
                sheet.write(r, 6, line.exchange_rate or 0, num_fmt)
                sheet.write(r, 7, line.inr_value or 0, num_fmt)
                sheet.write(r, 8, line.misc_amt or 0, num_fmt)
                sheet.write(r, 9, line.freight_amt or 0, num_fmt)
                sheet.write(r, 10, line.insurance_amt or 0, num_fmt)
                sheet.write(r, 11, line.assessable_value or 0, num_fmt)
                sheet.write(r, 12, line.bcd_amt or 0, num_fmt)
                sheet.write(r, 13, line.sws_amt or 0, num_fmt)
                sheet.write(r, 14, line.gst_amt or 0, num_fmt)
                sheet.write(r, 15, line.total_duty or 0, num_fmt)
                sheet.write(r, 16, line.report_id.sws_percent or 0, num_fmt_pct)
                sheet.write(r, 17, line.report_id.bcd_percent or 0, num_fmt_pct)
                sheet.write(r, 18, line.report_id.gst_percent or 0, num_fmt_pct)
                r += 1
            total_row = r
            sheet.write(r, 0, "", total_label_fmt)
            sheet.write(r, 1, "Total", total_label_fmt)
            for c in range(2, 6):
                sheet.write(r, c, "", total_label_fmt)
            sheet.write(r, 4, sum(l.qty or 0 for l in lines), total_fmt)
            sheet.write(r, 5, sum(l.usd_value or 0 for l in lines), total_fmt)
            for c in range(6, 15):
                sheet.write(r, c, "", total_label_fmt)
            sheet.write(r, 15, sum(l.total_duty or 0 for l in lines), total_fmt)
            for c in range(16, num_cols):
                sheet.write(r, c, "", total_label_fmt)
            r += 1
            return r, data_start, total_row

        # Standard Items
        standard = self.standard_line_ids
        if standard:
            row, std_data_start, std_total_row = write_section(
                standard,
                "Standard Items",
                "PO No: %s" % po_name,
                row,
                skip_section_header=False,
            )
            std_total_assessable = sum(l.assessable_value or 0 for l in standard)
            std_total_qty = sum(l.qty or 0 for l in standard)
            std_total_usd = sum(l.usd_value or 0 for l in standard)
            std_total_duty = sum(l.total_duty or 0 for l in standard)
        else:
            std_total_assessable = std_total_qty = std_total_usd = std_total_duty = 0
            row += 1

        # FOC section
        foc = self.foc_line_ids
        if foc:
            row += 1
            sheet.write(row, 0, partner_name, cell_fmt)
            row += 1
            sheet.write(row, 0, "PO No: %s - Free of Cost But duty is to be paid on assessable value" % po_name, cell_fmt)
            row += 1
            sheet.write(row, 0, "Freight", cell_fmt)
            sheet.write(row, 1, self.foc_freight or 0, num_fmt)
            row += 1
            sheet.write(row, 0, "Insurance", cell_fmt)
            sheet.write(row, 1, self.foc_insurance or 0, num_fmt)
            row += 1
            row, foc_data_start, foc_total_row = write_section(foc, "FOC", "", row, skip_section_header=True)
            foc_total_assessable = sum(l.assessable_value or 0 for l in foc)
        else:
            foc_total_assessable = 0
            row += 1

        # Grand total (Assessable Value)
        row += 1
        sheet.write(row, 0, "Grand Total (Assessable Value)", total_label_fmt)
        sheet.write(row, 11, std_total_assessable + foc_total_assessable, total_fmt)

        workbook.close()
        output.seek(0)
        return base64.b64encode(output.read())

    def action_download_xlsx(self):
        self.ensure_one()
        file_content = self._generate_xlsx()
        po_name = (self.purchase_order_id.name or "Report").replace("/", "-")
        name = "Net_Landing_Cost_%s.xlsx" % po_name
        attachment = self.env["ir.attachment"].create({
            "name": name,
            "type": "binary",
            "datas": file_content,
            "res_model": self._name,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") == "purchase.order" and self.env.context.get("active_id"):
            res["purchase_order_id"] = self.env.context["active_id"]
        return res

    @api.model_create_multi
    def create(self, vals_list):
        reports = super().create(vals_list)
        for report in reports:
            if report.purchase_order_id and not report.line_ids:
                report._fill_lines_from_po()
        return reports


class PurchaseLandingCostReportLine(models.TransientModel):
    _name = "purchase.landing.cost.report.line"
    _description = "Net Landing Cost Report Line"

    report_id = fields.Many2one("purchase.landing.cost.report", required=True, ondelete="cascade")
    purchase_order_line_id = fields.Many2one("purchase.order.line", string="PO Line", ondelete="cascade")
    sequence = fields.Integer(string="Sr No")
    product_id = fields.Many2one("product.product", string="Stock Item", required=True)
    is_foc = fields.Boolean(string="FOC", default=False)
    hsn_code = fields.Char(string="From PO HSN")
    usd_rate = fields.Float(string="From PO USD Rate", digits="Product Price", readonly=True)
    qty = fields.Float(string="From PO Qty", digits="Product Unit of Measure", readonly=True)
    usd_value = fields.Float(string="From PO USD Value", digits="Product Price", readonly=True)
    exchange_rate = fields.Float(string="Exchange Rate", digits=(16, 6), default=1.0)
    inr_value = fields.Float(string="INR Value", digits="Product Price", compute="_compute_landing_values", store=True)
    misc_amt = fields.Float(string="Misc", digits="Product Price", compute="_compute_landing_values", store=True)
    freight_amt = fields.Float(string="Freight", digits="Product Price", compute="_compute_landing_values", store=True)
    insurance_amt = fields.Float(string="Insurance", digits="Product Price", compute="_compute_landing_values", store=True)
    assessable_value = fields.Float(string="Assessable Value", digits="Product Price", compute="_compute_landing_values", store=True)
    bcd_amt = fields.Float(string="BCD", digits="Product Price", compute="_compute_landing_values", store=True)
    sws_amt = fields.Float(string="SWS", digits="Product Price", compute="_compute_landing_values", store=True)
    value_plus_cess_duty = fields.Float(string="Value + Cess + Duty", digits="Product Price", compute="_compute_landing_values", store=True)
    gst_amt = fields.Float(string="GST", digits="Product Price", compute="_compute_landing_values", store=True)
    total_duty = fields.Float(string="Total Duty", digits="Product Price", compute="_compute_landing_values", store=True)
    duty_before_gst = fields.Float(string="Total Duty (BCD+SWS)", digits="Product Price", compute="_compute_landing_values")
    display_section = fields.Char(compute="_compute_display_section")
    bcd_percent_display = fields.Float(related="report_id.bcd_percent", string="BCD % (Configurable)")
    sws_percent_display = fields.Float(related="report_id.sws_percent", string="SWS % (Configurable)")
    gst_percent_display = fields.Float(related="report_id.gst_percent", string="GST % (Configurable)")

    @api.depends("is_foc")
    def _compute_display_section(self):
        for line in self:
            line.display_section = _("Free of Cost") if line.is_foc else _("Standard")

    @api.depends(
        "usd_value", "exchange_rate",
        "report_id.misc", "report_id.freight", "report_id.insurance",
        "report_id.foc_freight", "report_id.foc_insurance",
        "report_id.bcd_percent", "report_id.sws_percent", "report_id.gst_percent",
    )
    def _compute_landing_values(self):
        for line in self:
            report = line.report_id
            if not report:
                line.inr_value = line.misc_amt = line.freight_amt = line.insurance_amt = 0
                line.assessable_value = line.bcd_amt = line.sws_amt = 0
                line.value_plus_cess_duty = line.gst_amt = line.total_duty = 0
                continue
            inr = (line.usd_value or 0) * (line.exchange_rate or 0)
            line.inr_value = inr
            non_foc = report.line_ids.filtered(lambda l: not l.is_foc)
            foc = report.line_ids.filtered(lambda l: l.is_foc)
            total_non_foc_usd = sum(non_foc.mapped("usd_value")) or 1
            total_foc_usd = sum(foc.mapped("usd_value")) or 1
            if line.is_foc:
                ratio = (line.usd_value or 0) / total_foc_usd
                misc_amt = 0.0
                freight_amt = ratio * (report.foc_freight or 0)
                insurance_amt = ratio * (report.foc_insurance or 0)
            else:
                ratio = (line.usd_value or 0) / total_non_foc_usd
                misc_amt = ratio * (report.misc or 0)
                freight_amt = ratio * (report.freight or 0)
                insurance_amt = ratio * (report.insurance or 0)
            line.misc_amt = misc_amt
            line.freight_amt = freight_amt
            line.insurance_amt = insurance_amt
            assessable = inr + misc_amt + freight_amt + insurance_amt
            line.assessable_value = assessable
            bcd = assessable * (report.bcd_percent or 0) / 100.0
            line.bcd_amt = bcd
            sws = bcd * (report.sws_percent or 0) / 100.0
            line.sws_amt = sws
            value_cess_duty = assessable + bcd + sws
            line.value_plus_cess_duty = value_cess_duty
            gst = value_cess_duty * (report.gst_percent or 0) / 100.0
            line.gst_amt = gst
            line.duty_before_gst = bcd + sws
            line.total_duty = bcd + sws + gst
