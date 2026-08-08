# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import _, api, Command, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare
from odoo.tools import SQL
from odoo.tools.date_utils import get_month

class PurchaseTDSWizard(models.TransientModel):
    _name = "purchase.tds.wizard"
    _description = "Purchase TDS Wizard"
    _check_company_auto = True

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        active_model = self._context.get('active_model')
        active_ids = self._context.get('active_ids', [])
        if active_model != 'purchase.order' or not active_ids:
            raise UserError(_("TDS must be created from a Purchase Order."))
        if len(active_ids) > 1:
            raise UserError(_("You can only create a TDS entry for one Purchase Order at a time."))
        purchase = self.env['purchase.order'].browse(active_ids[0])
        if purchase.state == 'cancel':
            raise UserError(_("You cannot create a TDS entry for a cancelled Purchase Order."))
        # 4. Set base fields
        result['purchase_id'] = purchase.id
        result['reference'] = _("TDS of %s", purchase.name)
        return result

    date = fields.Date(string="Date", default=fields.Date.context_today)
    purchase_id = fields.Many2one('purchase.order', string="Purchase Order", readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string="Company", compute='_compute_company_id')
    base = fields.Monetary(string="Base Amount")
    tax_id = fields.Many2one(comodel_name='account.tax', string="TDS Tax", required=True)
    amount = fields.Monetary(string="TDS Amount", compute='_compute_amount')
    currency_id = fields.Many2one(related='company_id.currency_id', string="Currency")
    reference = fields.Char(string="Reference")
    l10n_in_withholding_warning = fields.Json(string="Withholding warning", compute='_compute_l10n_in_withholding_warning')
    l10n_in_tcs_tds_warning = fields.Text(string="TDS/TCS Warning", compute="_compute_l10n_in_tcs_tds_warning")

    @api.depends('purchase_id', 'base', 'tax_id')
    def _compute_l10n_in_withholding_warning(self):
        for wizard in self:
            warnings = {}
            purchase = wizard.purchase_id
            if purchase:
                partner = purchase.partner_id.commercial_partner_id
                precision = wizard.currency_id.decimal_places
                if wizard.tax_id and wizard.tax_id.l10n_in_tds_tax_type == 'tds_purchase' and not partner.l10n_in_pan_entity_id:
                    warnings['lower_tds_tax'] = {'message': _("Please deduct TDS at higher rate if PAN is missing. Ignore if already applied.")}
                if float_compare(purchase.amount_untaxed, wizard.base, precision_digits=precision) < 0:
                    message = _("The base amount of TDS is greater than the amount of the purchase order")
                    warnings['lower_move_amount'] = {'message': message}
            wizard.l10n_in_withholding_warning = warnings

    @api.depends('purchase_id')
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.purchase_id.company_id

    @api.depends('tax_id', 'base')
    def _compute_amount(self):
        # Recomputes amount according to "base amount" and tax percentage
        for wizard in self:
            tax_amount = 0.0
            if wizard.tax_id:
                tax_amount = wizard._tax_compute_all_helper(wizard.base, wizard.tax_id)
            wizard.amount = tax_amount

    # === Helper methods ====
    @api.model
    def _tax_compute_all_helper(self, base, tax_id):
        # Computes the withholding tax amount provided a base and a tax
        # It is equivalent to: amount = self.base * self.tax_id.amount / 100
        taxes_res = tax_id.compute_all(
            base,
            currency=tax_id.company_id.currency_id,
            quantity=1.0,
            product=False,
            partner=False,
            is_refund=False,
        )
        tax_amount = taxes_res['total_included'] - taxes_res['total_excluded']
        tax_amount = abs(tax_amount)
        return tax_amount

    def action_confirm_tds(self):
        self.ensure_one()
        if not self.tax_id:
            raise ValidationError(_("Please select a TDS Tax."))
        if self.base <= 0:
            raise ValidationError(_("Please enter a valid TDS Base Amount."))
        if self.amount <= 0:
            raise ValidationError(_("TDS Amount must be greater than zero."))
        self.env['purchase.tds'].create({
            'purchase_id': self.purchase_id.id,
            'date': self.date,
            'tax_id': self.tax_id.id,
            'base': self.base,
            'reference': self.reference,
        })
        self.purchase_id.write({"tds_tax_id": self.tax_id.id})
        return {'type': 'ir.actions.act_window_close'}

    def _get_sections_aggregate_sum_by_pan(self, section_alert):
        self.ensure_one()
        purchase = self.purchase_id
        company = purchase.company_id
        commercial_partner = purchase.partner_id.commercial_partner_id
        date = (
            purchase.date_order.date()
            if purchase.date_order
            else fields.Date.context_today(self)
        )
        month_start_date, month_end_date = get_month(date)
        fiscalyear_dates = company.sudo().compute_fiscalyear_dates(date)
        fiscalyear_start_date = fiscalyear_dates["date_from"]
        fiscalyear_end_date = fiscalyear_dates["date_to"]
        default_domain = [
            ("company_id", "child_of", company.root_id.id),
            ("order_id.state", "!=", "cancel"),
        ]
        if commercial_partner.l10n_in_pan:
            default_domain += [
                (
                    "order_id.partner_id.commercial_partner_id.l10n_in_pan",
                    "=",
                    commercial_partner.l10n_in_pan,
                )
            ]
        else:
            default_domain += [
                (
                    "order_id.partner_id.commercial_partner_id",
                    "=",
                    commercial_partner.id,
                )
            ]
        frequency_domains = {
            "monthly": [
                ("order_id.date_order", ">=", month_start_date),
                ("order_id.date_order", "<=", month_end_date),
            ],
            "fiscal_yearly": [
                ("order_id.date_order", ">=", fiscalyear_start_date),
                ("order_id.date_order", "<=", fiscalyear_end_date),
            ],
        }
        aggregate_result = {}
        for frequency, frequency_domain in frequency_domains.items():
            lines = self.env["purchase.order.line"].search(
                default_domain + frequency_domain
            )
            if section_alert.consider_amount == "total_amount":
                total = sum(lines.mapped("price_total"))
            else:
                total = sum(lines.mapped("price_subtotal"))
            aggregate_result[frequency] = {
                "balance": total,
                "price_total": total,
            }
        return aggregate_result

    @api.depends(
        "purchase_id",
        "purchase_id.date_order",
        "purchase_id.partner_id",
        "purchase_id.order_line.price_subtotal",
        "purchase_id.order_line.price_total",
        "tax_id",
    )
    def _compute_l10n_in_tcs_tds_warning(self):
        for wizard in self:
            wizard.l10n_in_tcs_tds_warning = False
            purchase = wizard.purchase_id
            if not purchase:
                continue
            if purchase.company_id.country_id.code != "IN":
                continue
            if not wizard.tax_id:
                continue
            section_alert = wizard.tax_id.l10n_in_section_id
            if not section_alert:
                continue
            if section_alert.tax_source_type != "tds":
                continue
            if any(tds.tax_id == wizard.tax_id for tds in purchase.tds_ids):
                continue
            # Current PO amount
            if section_alert.consider_amount == "total_amount":
                lines_total = sum(
                    purchase.order_line.mapped("price_total")
                )
            else:
                lines_total = sum(
                    purchase.order_line.mapped("price_subtotal")
                )
            warning = False
            # Per Transaction
            if (
                    section_alert.is_per_transaction_limit
                    and lines_total > section_alert.per_transaction_limit
            ):
                warning = True
            # Aggregate
            if section_alert.is_aggregate_limit:
                threshold_sums = (
                    wizard._get_sections_aggregate_sum_by_pan(
                        section_alert
                    )
                )
                aggregate_period_key = (
                    "price_total"
                    if section_alert.consider_amount == "total_amount"
                    else "balance"
                )
                aggregate_total = (
                    threshold_sums
                    .get(section_alert.aggregate_period, {})
                    .get(aggregate_period_key, 0.0)
                )
                # Current PO is already included in the PO query
                if aggregate_total > section_alert.aggregate_limit:
                    warning = True
            if warning:
                wizard.l10n_in_tcs_tds_warning = (section_alert._get_warning_message())

