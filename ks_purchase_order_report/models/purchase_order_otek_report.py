# -*- coding: utf-8 -*-
# Report source: doc/REPORT_SOURCE_PU001.md — Row 3 = description, Row 4 = column name.

from datetime import datetime, time

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .report_source_pu001 import PU001_COLUMNS, PU001_FIELD_NAMES

# field_name -> (string=Row 4, help=Row 3)
_PU001_FIELD_INFO = {
    fname: (row4, row3) for fname, (row3, row4) in zip(PU001_FIELD_NAMES, PU001_COLUMNS)
}


def _get_line_igst(line):
    """Get IGST tax amount for a purchase order line."""
    base_line = line._prepare_base_line_for_taxes_computation()
    line.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
    tax_details = base_line.get('tax_details', {})
    taxes_data = tax_details.get('taxes_data', [])
    igst = 0.0
    for tax_data in taxes_data:
        tax = tax_data.get('tax')
        if tax and 'IGST' in (tax.name or '').upper():
            igst += tax_data.get('tax_amount_currency', 0.0)
    return igst


class PurchaseOrderOtekReportWizard(models.TransientModel):
    _name = 'ks.purchase.order.otek.report.wizard'
    _description = 'Otek Purchase Order Report Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today,
    )

    def _get_otek_pol_domain(self):
        """Domain for purchase order lines: Otek brand + date_order in range."""
        brand = self.env['product.brand'].sudo().search([('name', '=ilike', 'otek')], limit=1)
        if not brand:
            raise UserError(_("Brand 'Otek' not found. Please create the brand first."))
        return [
            ('order_id.state', '!=', 'cancel'),
            ('product_id.product_tmpl_id.brand_id', '=', brand.id),
            ('display_type', '=', False),
            ('order_id.date_order', '>=', datetime.combine(self.date_from, time.min)),
            ('order_id.date_order', '<=', datetime.combine(self.date_to, time.max)),
        ]

    def action_show_report(self):
        """Create report lines and open tree view."""
        self.ensure_one()
        pol_domain = self._get_otek_pol_domain()
        pol_lines = self.env['purchase.order.line'].sudo().search(pol_domain, order='order_id, id')
        if not pol_lines:
            raise UserError(_("No purchase order lines found with Otek brand products in the selected date range."))

        ReportLine = self.env['ks.purchase.order.otek.report.line'].sudo()
        ReportLine.search([('wizard_id', '=', self.id)]).unlink()

        for line in pol_lines:
            order = line.sudo().order_id.sudo()
            product = line.sudo().product_id.sudo()
            product_template = product.sudo().product_tmpl_id.sudo()
            qty = line.product_qty or 0.0
            if order.is_exchange:
                rate = order.rate
            else:
                date_rate = self.env['res.currency.rate'].search([('name','=',order.date_approve), ('company_id', '=', order.company_id.id),('currency_id', '=', order.currency_id.id)])
                if date_rate:
                    rate = date_rate
                else:
                    rate = 0
            price_unit = line.price_unit or 0.0
            fob = rate * price_unit
            amount = rate * qty if rate else 0.0
            if order.invoice_ids:
                for bill in order.invoice_ids:
                    payment = sum(bill.reconciled_payment_ids.mapped('amount'))
            else:
                payment = 0
            payment = payment
            balance = amount - payment
            conversion_rate = 1.0
            inr_amount = conversion_rate * amount
            igst = _get_line_igst(line)
            ReportLine.create({
                'wizard_id': self.id,
                'order_id': order.id,
                'order_line_id': line.id,
                'supplier': order.partner_id.name or '',
                'product_categ': product_template.categ_id.name if product_template.categ_id else '',
                'product': product_template.name or product.name or '',
                'qty': qty,
                'fob': fob,
                'amount': amount,
                'payment': payment,
                'balance': balance,
                'inr_amount': inr_amount,
                'freight_ins': 0.0,
                'bcd': 0.0,
                'sws': 0.0,
                'igst': igst,
                'fine_interest': 0.0,
            })

        return self._action_open_tree()

    def _action_open_tree(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Otek Purchase Order Report'),
            'res_model': 'ks.purchase.order.otek.report.line',
            'view_mode': 'list',
            'domain': [('wizard_id', '=', self.id)],
            'context': {
                'search_default_wizard_id': self.id,
                'active_wizard_id': self.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
            },
        }


class PurchaseOrderOtekReportLine(models.TransientModel):
    _name = 'ks.purchase.order.otek.report.line'
    _description = 'Otek Purchase Order Report Line'

    wizard_id = fields.Many2one(
        'ks.purchase.order.otek.report.wizard',
        string='Wizard',
        ondelete='cascade',
        required=True,
    )
    order_id = fields.Many2one(
        'purchase.order',
        string=_PU001_FIELD_INFO['order_id'][0],
        ondelete='cascade',
        help=_PU001_FIELD_INFO['order_id'][1],
    )
    order_line_id = fields.Many2one(
        'purchase.order.line',
        string='Order Line',
        ondelete='cascade',
    )
    supplier = fields.Char(
        string=_PU001_FIELD_INFO['supplier'][0],
        help=_PU001_FIELD_INFO['supplier'][1],
    )
    product_categ = fields.Char(
        string=_PU001_FIELD_INFO['product_categ'][0],
        help=_PU001_FIELD_INFO['product_categ'][1],
    )
    product = fields.Char(
        string=_PU001_FIELD_INFO['product'][0],
        help=_PU001_FIELD_INFO['product'][1],
    )
    qty = fields.Float(
        string=_PU001_FIELD_INFO['qty'][0],
        digits='Product Unit of Measure',
        help=_PU001_FIELD_INFO['qty'][1],
    )
    fob = fields.Float(
        string=_PU001_FIELD_INFO['fob'][0],
        digits=(16, 6),
        help=_PU001_FIELD_INFO['fob'][1],
    )
    amount = fields.Float(
        string=_PU001_FIELD_INFO['amount'][0],
        digits='Product Price',
        help=_PU001_FIELD_INFO['amount'][1],
    )
    payment = fields.Float(
        string=_PU001_FIELD_INFO['payment'][0],
        digits='Product Price',
        help=_PU001_FIELD_INFO['payment'][1],
    )
    balance = fields.Float(
        string=_PU001_FIELD_INFO['balance'][0],
        digits='Product Price',
        help=_PU001_FIELD_INFO['balance'][1],
    )
    inr_amount = fields.Float(
        string=_PU001_FIELD_INFO['inr_amount'][0],
        digits='Product Price',
        help=_PU001_FIELD_INFO['inr_amount'][1],
    )
    freight_ins = fields.Float(
        string=_PU001_FIELD_INFO['freight_ins'][0],
        digits='Product Price',
        help=_PU001_FIELD_INFO['freight_ins'][1],
    )
    bcd = fields.Float(
        string=_PU001_FIELD_INFO['bcd'][0],
        digits='Product Price',
        help=_PU001_FIELD_INFO['bcd'][1],
    )
    sws = fields.Float(
        string=_PU001_FIELD_INFO['sws'][0],
        digits='Product Price',
        help=_PU001_FIELD_INFO['sws'][1],
    )
    igst = fields.Float(
        string=_PU001_FIELD_INFO['igst'][0],
        digits='Account',
        help=_PU001_FIELD_INFO['igst'][1],
    )
    fine_interest = fields.Float(
        string=_PU001_FIELD_INFO['fine_interest'][0],
        digits='Product Price',
        help=_PU001_FIELD_INFO['fine_interest'][1],
    )
    total_exp = fields.Float(
        string=_PU001_FIELD_INFO['total_exp'][0],
        digits='Account',
        compute='_compute_total_exp_per_pc',
        store=True,
        help=_PU001_FIELD_INFO['total_exp'][1],
    )
    per_pc_landed_cost = fields.Float(
        string=_PU001_FIELD_INFO['per_pc_landed_cost'][0],
        digits='Product Price',
        compute='_compute_total_exp_per_pc',
        store=True,
        help=_PU001_FIELD_INFO['per_pc_landed_cost'][1],
    )

    @api.depends('freight_ins', 'bcd', 'sws', 'igst', 'fine_interest', 'inr_amount', 'qty')
    def _compute_total_exp_per_pc(self):
        for rec in self:
            rec.total_exp = (
                (rec.freight_ins or 0.0)
                + (rec.bcd or 0.0)
                + (rec.sws or 0.0)
                + (rec.igst or 0.0)
                + (rec.fine_interest or 0.0)
            )
            qty = rec.qty or 0.0
            if qty:
                rec.per_pc_landed_cost = (rec.total_exp + (rec.inr_amount or 0.0)) / qty
            else:
                rec.per_pc_landed_cost = 0.0

    def action_export_xlsx(self):
        """Export selected (or all in context) report lines to Excel."""
        if self:
            line_ids = self.ids
        else:
            wizard_id = self.env.context.get('active_wizard_id')
            if wizard_id:
                lines = self.search([('wizard_id', '=', wizard_id)])
                line_ids = lines.ids
            else:
                line_ids = []
        if not line_ids:
            raise UserError(_("No lines to export."))
        base_url = self.env.company.get_base_url()
        url = f"{base_url}/purchase_order/export_otek_xlsx?line_ids={','.join(str(i) for i in line_ids)}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }
