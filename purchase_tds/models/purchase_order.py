# -*- coding: utf-8 -*-
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
    tds_tax_id = fields.Many2one("account.tax", string="TDS Tax", readonly=1)
    tds_section = fields.Many2one("l10n_in.section.alert", string="TDS Section", related="tds_tax_id.l10n_in_section_id", store=True, readonly=True)
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

    @api.depends('tds_ids')
    def _compute_tds_count(self):
        for order in self:
            order.tds_count = len(order.tds_ids)

    @api.depends('amount_total', 'tds_ids.base', 'tds_ids.amount')
    def _compute_tds_amounts(self):
        for order in self:
            amount_tds = sum(order.tds_ids.mapped('amount'))
            order.amount_tds = amount_tds
            order.amount_net_payable = order.amount_total - amount_tds

    def action_deduct_tds(self):
        self.ensure_one()
        if self.state == 'cancel':
            raise UserError(_("You cannot deduct TDS on a cancelled Purchase Order."))
        if not self.partner_id:
            raise UserError(_("Please select a Vendor before deducting TDS."))
        if self.amount_total <= 0:
            raise UserError(_("Purchase Order total must be greater than zero to deduct TDS."))

        company = self.company_id
        root_company = company.root_id or company
        commercial_partner = self.partner_id.commercial_partner_id

        # 1. Determine fiscal year date range based on order date
        order_date = self.date_order.date() if self.date_order else fields.Date.context_today(self)
        fiscalyear_dates = root_company.sudo().compute_fiscalyear_dates(order_date)
        fiscalyear_start_date = fiscalyear_dates["date_from"]
        fiscalyear_end_date = fiscalyear_dates["date_to"]

        # 2. Section 194Q lookup
        section_194q = self.env['l10n_in.section.alert'].search([('name', '=', '(ACT 1961) 194Q')], limit=1)
        if not section_194q:
            section_194q = self.env.ref('l10n_in_withholding.tds_section_194q', raise_if_not_found=False)
        if not section_194q:
            section_194q = self.env['l10n_in.section.alert'].search([('name', 'ilike', '194Q')], limit=1)

        threshold = (section_194q and section_194q.aggregate_limit) or 5000000.0

        # 3. Find prior qualifying POs across main company and all sub-companies using sudo()
        # to bypass multi-company record rules so all branch records are counted in cumulative total
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
        prior_orders = all_po_in_fy.filtered(lambda po: po.id != self.id and (
            (po.date_order < current_date_order) or
            (po.date_order == current_date_order and (not self.id or po.id < self.id))
        ))

        # Section 194Q u/s Indian Income Tax Act applies on UNTAXED amount (purchase value excl. GST).
        # Using amount_untaxed ensures:
        # 1. Calculation is stable on repeated clicks (amount_untaxed never changes unlike amount_total
        #    which could appear different after TDS recomputation caching).
        # 2. Consistent with l10n_in.section.alert consider_amount = 'untaxed_amount' for 194Q.
        consider_amount = (section_194q and section_194q.consider_amount) or 'untaxed_amount'
        if consider_amount == 'total_amount':
            prior_total = sum(prior_orders.mapped("amount_total"))
            current_total = self.amount_total
        else:
            prior_total = sum(prior_orders.mapped("amount_untaxed"))
            current_total = self.amount_untaxed

        cumulative_total = prior_total + current_total

        # 4. Check threshold condition
        if cumulative_total <= threshold:
            currency_symbol = self.currency_id.symbol or ""
            amount_label = _("(Incl. Tax)") if consider_amount == 'total_amount' else _("(Excl. Tax)")
            raise UserError(_(
                "TDS under Section (ACT 1961) 194Q is not applicable.\n\n"
                "• Prior purchases across %(company)s group (%(count)d order(s)) %(label)s: %(symbol)s %(prior)s\n"
                "• Current PO untaxed amount %(label)s: %(symbol)s %(current)s\n"
                "• Cumulative purchases in FY %(label)s: %(symbol)s %(cumulative)s\n"
                "• Section 194Q Threshold: %(symbol)s %(threshold)s\n\n"
                "The cumulative total does not exceed the threshold limit of %(symbol)s %(threshold)s.",
                company=root_company.name,
                count=len(prior_orders),
                label=amount_label,
                symbol=currency_symbol,
                prior=f"{prior_total:,.2f}",
                current=f"{current_total:,.2f}",
                cumulative=f"{cumulative_total:,.2f}",
                threshold=f"{threshold:,.2f}",
            ))

        if prior_total < threshold:
            # Threshold crossed in this purchase order — TDS base is the excess above threshold
            base_amount = cumulative_total - threshold
        else:
            # Threshold already fully crossed in prior orders — TDS base is full current PO untaxed amount
            base_amount = current_total

        # 5. Find Section 194Q Purchase Tax (matches '0.1% TDS 194Q P')
        # In Odoo Indian withholding, TDS purchase taxes have type_tax_use='none' and l10n_in_tds_tax_type='purchase'
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

        if not tax:
            raise UserError(_(
                "No TDS purchase tax found for '0.1%% TDS 194Q P' in company %s.",
                company.name,
            ))

        # Ensure section_id is linked on tax if available so PO displays TDS section
        if section_194q and not tax.l10n_in_section_id:
            tax.sudo().write({"l10n_in_section_id": section_194q.id})

        # 6. Auto-create or update purchase.tds entry
        tds_vals = {
            "date": self.date_order.date() if self.date_order else fields.Date.context_today(self),
            "tax_id": tax.id,
            "base": base_amount,
            "reference": _("TDS 194Q of %s", self.name),
        }

        if self.tds_ids:
            self.tds_ids[0].write(tds_vals)
            if len(self.tds_ids) > 1:
                (self.tds_ids - self.tds_ids[0]).unlink()
            tds_entry = self.tds_ids[0]
            self.write({"tds_tax_id": tax.id})
        else:
            self.write({
                "tds_ids": [Command.create(tds_vals)],
                "tds_tax_id": tax.id,
            })
            tds_entry = self.tds_ids[0]

        # Force recomputation of fields on self
        self._compute_tds_count()
        self._compute_tds_amounts()

        currency_symbol = self.currency_id.symbol or ""
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
                    count=len(prior_orders),
                    company=root_company.name,
                    cumulative=f"{cumulative_total:,.2f}",
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

