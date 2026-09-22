# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.tools.date_utils import get_month

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    tds_ids = fields.One2many(
        'purchase.tds',
        'purchase_id',
        string='TDS Entries',
    )
    tds_tax_id = fields.Many2one(
        "account.tax",
        string="TDS Tax",
        compute='_compute_tds_tax_id',
        store=True,
        readonly=True,
    )
    tds_section = fields.Many2one(
        "l10n_in.section.alert",
        string="TDS Section",
        related="tds_tax_id.l10n_in_section_id",
        store=True,
        readonly=True,
    )
    amount_tds = fields.Monetary(
            string="TDS Amount",
            compute='_compute_tds_amounts',
            store=True,
            currency_field='currency_id'
    )
    amount_net_payable = fields.Monetary(
        string="Net Payable Amount",
        compute='_compute_tds_amounts',
        store=True,
        currency_field='currency_id'
    )
    tds_count = fields.Integer(
        compute='_compute_tds_count',
    )
    tds_eligible_warning = fields.Char(
        string="TDS Eligibility Warning",
        compute='_compute_tds_warnings',
    )
    tds_mismatch_warning = fields.Char(
        string="TDS Mismatch Warning",
        compute='_compute_tds_warnings',
    )

    def action_view_tds(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Purchase TDS'),
            'res_model': 'purchase.tds',
            'view_mode': 'list,form',
            'domain': [('purchase_id', '=', self.id)],
            'context': {
                'default_purchase_id': self.id,
            },
        }
        if len(self.tds_ids) == 1:
            form_view = self.env.ref('purchase_tds.view_purchase_tds_form', raise_if_not_found=False)
            action['views'] = [(form_view.id, 'form')] if form_view else [(False, 'form')]
            action['res_id'] = self.tds_ids.id
        return action

    @api.depends('tds_ids.tax_id')
    def _compute_tds_tax_id(self):
        for order in self:
            order.tds_tax_id = order.tds_ids[0].tax_id if order.tds_ids else False

    @api.depends('tds_ids')
    def _compute_tds_count(self):
        for order in self:
            order.tds_count = len(order.tds_ids)

    @api.depends('amount_total', 'tds_ids', 'tds_ids.base', 'tds_ids.amount')
    def _compute_tds_amounts(self):
        for order in self:
            amount_tds = sum(order.tds_ids.mapped('amount'))
            order.amount_tds = amount_tds
            order.amount_net_payable = order.amount_total - amount_tds

    def _get_tds_expected_calculation(self):
        self.ensure_one()
        company = self.company_id
        root_company = company.root_id or company
        commercial_partner = self.partner_id.commercial_partner_id

        res = {
            'eligible': False,
            'prior_total': 0.0,
            'current_total': 0.0,
            'cumulative_total': 0.0,
            'threshold': 5000000.0,
            'base_amount': 0.0,
            'tax': False,
            'root_company': root_company,
            'prior_orders': self.env['purchase.order'],
            'section_194q': False,
            'consider_amount': 'untaxed_amount',
            'amount_label': _("(Excl. Tax)"),
        }

        if self.state == 'cancel' or not self.partner_id or self.amount_untaxed <= 0:
            return res

        # 1. Determine fiscal year date range based on order date
        order_date = self.date_order.date() if self.date_order else fields.Date.context_today(self)
        try:
            fiscalyear_dates = root_company.sudo().compute_fiscalyear_dates(order_date)
            fiscalyear_start_date = fiscalyear_dates["date_from"]
            fiscalyear_end_date = fiscalyear_dates["date_to"]
        except Exception:
            fiscalyear_start_date = order_date.replace(month=4, day=1) if order_date.month >= 4 else order_date.replace(year=order_date.year - 1, month=4, day=1)
            fiscalyear_end_date = fiscalyear_start_date.replace(year=fiscalyear_start_date.year + 1, month=3, day=31)

        # 2. Section 194Q lookup
        section_194q = self.env['l10n_in.section.alert'].search([('name', '=', '(ACT 1961) 194Q')], limit=1)
        if not section_194q:
            section_194q = self.env.ref('l10n_in_withholding.tds_section_194q', raise_if_not_found=False)
        if not section_194q:
            section_194q = self.env['l10n_in.section.alert'].search([('name', 'ilike', '194Q')], limit=1)

        threshold = (section_194q and section_194q.aggregate_limit) or 5000000.0
        res['threshold'] = threshold
        res['section_194q'] = section_194q

        # 3. Find prior qualifying POs across main company and all sub-companies using sudo()
        domain = [
            ("company_id", "child_of", root_company.id),
            ("state", "!=", "cancel"),
            ("date_order", ">=", fiscalyear_start_date),
            ("date_order", "<=", fiscalyear_end_date),
        ]
        vendor_pan = commercial_partner.l10n_in_pan or (
            commercial_partner.vat and len(commercial_partner.vat) >= 12 and commercial_partner.vat[2:12]
        )
        if vendor_pan:
            domain += [
                "|",
                ("partner_id.commercial_partner_id.l10n_in_pan", "=", vendor_pan),
                ("partner_id.commercial_partner_id", "=", commercial_partner.id),
            ]
        else:
            domain.append(("partner_id.commercial_partner_id", "=", commercial_partner.id))

        all_po_in_fy = self.env['purchase.order'].sudo().search(domain, order="date_order asc, id asc")

        # Prior POs are all orders preceding this order in the fiscal year
        current_date_order = self.date_order or fields.Datetime.now()
        origin_id = self._origin.id if hasattr(self, '_origin') and self._origin else self.id
        prior_orders = all_po_in_fy.filtered(lambda po: po.id != origin_id and (
            (po.date_order < current_date_order) or
            (po.date_order == current_date_order and (not origin_id or po.id < origin_id))
        ))
        res['prior_orders'] = prior_orders

        consider_amount = (section_194q and section_194q.consider_amount) or 'untaxed_amount'
        res['consider_amount'] = consider_amount
        res['amount_label'] = _("(Incl. Tax)") if consider_amount == 'total_amount' else _("(Excl. Tax)")

        if consider_amount == 'total_amount':
            prior_total = sum(prior_orders.mapped("amount_total"))
            current_total = self.amount_total
        else:
            prior_total = sum(prior_orders.mapped("amount_untaxed"))
            current_total = self.amount_untaxed

        cumulative_total = prior_total + current_total
        res['prior_total'] = prior_total
        res['current_total'] = current_total
        res['cumulative_total'] = cumulative_total

        if cumulative_total > threshold:
            res['eligible'] = True
            if prior_total < threshold:
                res['base_amount'] = cumulative_total - threshold
            else:
                res['base_amount'] = current_total
        else:
            res['eligible'] = False
            res['base_amount'] = 0.0

        # Find tax
        tax = self.env["account.tax"].search([
            ("company_id", "in", [company.id, root_company.id]),
            ("name", "=ilike", "0.1% TDS 194Q P%"),
        ], limit=1)

        if not tax and section_194q:
            tax = self.env["account.tax"].search([
                ("company_id", "in", [company.id, root_company.id]),
                ("l10n_in_section_id", "=", section_194q.id),
                "|",
                ("l10n_in_tds_tax_type", "=", "purchase"),
                ("name", "not ilike", " 194Q S"),
            ], limit=1)

        if not tax:
            tax = self.env["account.tax"].search([
                ("company_id", "in", [company.id, root_company.id]),
                ("name", "ilike", "194Q"),
                ("name", "not ilike", " 194Q S"),
                "|",
                ("l10n_in_tds_tax_type", "=", "purchase"),
                ("name", "ilike", "% P"),
            ], limit=1)

        if not tax:
            tax = self.env["account.tax"].search([
                ("name", "=ilike", "0.1% TDS 194Q P%"),
            ], limit=1)

        res['tax'] = tax
        return res

    @api.depends(
        'state',
        'partner_id',
        'date_order',
        'amount_untaxed',
        'amount_total',
        'order_line.price_unit',
        'order_line.product_qty',
        'order_line.price_subtotal',
        'tds_ids',
        'tds_ids.base',
        'tds_ids.amount',
    )
    def _compute_tds_warnings(self):
        for order in self:
            order.tds_eligible_warning = False
            order.tds_mismatch_warning = False

            if order.state == 'cancel' or not order.partner_id or order.amount_untaxed <= 0:
                continue

            calc = order._get_tds_expected_calculation()
            currency_symbol = order.currency_id.symbol or ""

            # Case 1: PO is eligible for TDS under Section 194Q, but TDS has not been deducted yet
            if calc['eligible'] and not order.tds_ids:
                order.tds_eligible_warning = _(
                    "This Purchase Order is eligible for TDS deduction under Section (ACT 1961) 194Q. "
                    "Cumulative purchases in FY across under Company: %(company)s: %(symbol)s %(cumulative)s (Threshold: %(symbol)s %(threshold)s). "
                    "Expected TDS Base: %(symbol)s %(base)s.",
                    company=calc['root_company'].name,
                    symbol=currency_symbol,
                    cumulative=f"{calc['cumulative_total']:,.2f}",
                    threshold=f"{calc['threshold']:,.2f}",
                    base=f"{calc['base_amount']:,.2f}",
                )

            # Case 2: TDS was already deducted, but PO lines/unit price were updated and TDS base/amount no longer matches
            elif order.tds_ids:
                current_tds_base = order.tds_ids[0].base
                expected_base = calc['base_amount'] if calc['eligible'] else 0.0
                if abs(current_tds_base - expected_base) > 0.01:
                    order.tds_mismatch_warning = _(
                        "TDS Amount Mismatch: Purchase Order untaxed amount has changed (Current Untaxed: %(symbol)s %(untaxed)s). "
                        "Deducted TDS Base (%(symbol)s %(current_base)s) does not match Expected Base (%(symbol)s %(expected_base)s). "
                        "Please click 'Deduct TDS' to update.",
                        symbol=currency_symbol,
                        untaxed=f"{order.amount_untaxed:,.2f}",
                        current_base=f"{current_tds_base:,.2f}",
                        expected_base=f"{expected_base:,.2f}",
                    )

    def action_deduct_tds(self):
        self.ensure_one()
        if self.state == 'cancel':
            raise UserError(_("You cannot deduct TDS on a cancelled Purchase Order."))
        if not self.partner_id:
            raise UserError(_("Please select a Vendor before deducting TDS."))
        if self.amount_total <= 0:
            raise UserError(_("Purchase Order total must be greater than zero to deduct TDS."))

        calc = self._get_tds_expected_calculation()

        if not calc['eligible']:
            currency_symbol = self.currency_id.symbol or ""
            raise UserError(_(
                "TDS under Section (ACT 1961) 194Q is not applicable.\n\n"
                "• Prior purchases across %(company)s group (%(count)d order(s)) %(label)s: %(symbol)s %(prior)s\n"
                "• Current PO untaxed amount %(label)s: %(symbol)s %(current)s\n"
                "• Cumulative purchases in FY %(label)s: %(symbol)s %(cumulative)s\n"
                "• Section 194Q Threshold: %(symbol)s %(threshold)s\n\n"
                "The cumulative total does not exceed the threshold limit of %(symbol)s %(threshold)s.",
                company=calc['root_company'].name,
                count=len(calc['prior_orders']),
                label=calc['amount_label'],
                symbol=currency_symbol,
                prior=f"{calc['prior_total']:,.2f}",
                current=f"{calc['current_total']:,.2f}",
                cumulative=f"{calc['cumulative_total']:,.2f}",
                threshold=f"{calc['threshold']:,.2f}",
            ))

        tax = calc['tax']
        if not tax:
            raise UserError(_(
                "No TDS purchase tax found for '0.1%% TDS 194Q P' in company %s.",
                self.company_id.name,
            ))

        section_194q = calc['section_194q']
        if section_194q and not tax.l10n_in_section_id:
            tax.sudo().write({"l10n_in_section_id": section_194q.id})

        base_amount = calc['base_amount']

        # Auto-create or update purchase.tds entry
        tds_vals = {
            "date": self.date_order.date() if self.date_order else fields.Date.context_today(self),
            "tax_id": tax.id,
            "base": base_amount,
            "reference": _("TDS 194Q of %s", self.name),
        }

        is_new = not bool(self.tds_ids)
        if self.tds_ids:
            self.tds_ids[0].with_context(skip_tds_chatter=True).write(tds_vals)
            if len(self.tds_ids) > 1:
                (self.tds_ids - self.tds_ids[0]).with_context(skip_tds_chatter=True).unlink()
            tds_entry = self.tds_ids[0]
        else:
            self.with_context(skip_tds_chatter=True).write({
                "tds_ids": [Command.create(tds_vals)],
            })
            tds_entry = self.tds_ids[0]

        # Force recomputation of fields on self
        self._compute_tds_tax_id()
        self._compute_tds_count()
        self._compute_tds_amounts()
        self._compute_tds_warnings()

        # Log in Purchase Order Chatter
        currency_symbol = self.currency_id.symbol or ""
        chatter_title = _("TDS (ACT 1961) 194Q Deducted") if is_new else _("TDS (ACT 1961) 194Q Recomputed")
        self.message_post(
            body=Markup(
                "<b>%(title)s</b><br/>"
                "<ul>"
                "<li><b>Tax:</b> %(tax)s</li>"
                "<li><b>TDS Base Amount (Excl. Tax):</b> %(symbol)s %(base)s</li>"
                "<li><b>TDS Amount:</b> %(symbol)s %(amount)s</li>"
                "<li><b>Net Payable:</b> %(symbol)s %(net_payable)s</li>"
                "<li><b>Cumulative FY Purchases across %(company)s:</b> %(symbol)s %(cumulative)s</li>"
                "</ul>"
            ) % {
                "title": chatter_title,
                "tax": tax.display_name,
                "symbol": currency_symbol,
                "base": f"{base_amount:,.2f}",
                "amount": f"{tds_entry.amount:,.2f}",
                "net_payable": f"{self.amount_net_payable:,.2f}",
                "company": calc['root_company'].name,
                "cumulative": f"{calc['cumulative_total']:,.2f}",
            },
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("TDS Deducted Successfully"),
                "message": _(
                    "Section: (ACT 1961) 194Q\n"
                    "Cumulative Total (%(count)d prior order(s) across %(company)s) (Excl. Tax): %(symbol)s %(cumulative)s\n"
                    "TDS Base Amount (Excl. Tax): %(symbol)s %(base)s\n"
                    "Tax: %(tax)s\n"
                    "TDS Amount: %(symbol)s %(amount)s",
                    count=len(calc['prior_orders']),
                    company=calc['root_company'].name,
                    cumulative=f"{calc['cumulative_total']:,.2f}",
                    base=f"{base_amount:,.2f}",
                    tax=tax.name,
                    symbol=currency_symbol,
                    amount=f"{tds_entry.amount:,.2f}",
                ),
                "type": "success",
                "sticky": False,
                "next": {
                    "type": "ir.actions.client",
                    "tag": "reload",
                },
            },
        }

