# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


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
