# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    purchase_tds_ids = fields.One2many(
        'purchase.tds',
        'bill_id',
        string='Purchase TDS Entries',
    )
    purchase_tds_count = fields.Integer(
        string='PO TDS Count',
        compute='_compute_purchase_tds_count',
    )
    po_tds_amount = fields.Monetary(
        string="PO TDS Amount",
        compute='_compute_purchase_tds_details',
        currency_field='currency_id',
    )
    po_tds_base = fields.Monetary(
        string="PO TDS Base Amount",
        compute='_compute_purchase_tds_details',
        currency_field='currency_id',
    )
    po_tds_tax_id = fields.Many2one(
        'account.tax',
        string="PO TDS Tax",
        compute='_compute_purchase_tds_details',
    )
    po_tds_section = fields.Many2one(
        'l10n_in.section.alert',
        string="PO TDS Section",
        compute='_compute_purchase_tds_details',
    )

    @api.depends('purchase_tds_ids', 'invoice_line_ids.purchase_line_id')
    def _compute_purchase_tds_count(self):
        for move in self:
            if move.move_type == 'in_invoice' and move.id and not isinstance(move.id, models.NewId):
                source_pos = move.invoice_line_ids.mapped('purchase_line_id.order_id')
                unlinked_tds = source_pos.mapped('tds_ids').filtered(lambda t: not t.bill_id)
                if unlinked_tds:
                    unlinked_tds.sudo().write({'bill_id': move.id})
            move.purchase_tds_count = len(move.purchase_tds_ids)

    @api.depends('purchase_tds_ids', 'purchase_tds_ids.amount', 'purchase_tds_ids.base', 'purchase_tds_ids.tax_id')
    def _compute_purchase_tds_details(self):
        for move in self:
            if move.purchase_tds_ids:
                tds = move.purchase_tds_ids[0]
                move.po_tds_amount = sum(move.purchase_tds_ids.mapped('amount'))
                move.po_tds_base = tds.base
                move.po_tds_tax_id = tds.tax_id
                move.po_tds_section = tds.tax_id.l10n_in_section_id
            else:
                move.po_tds_amount = 0.0
                move.po_tds_base = 0.0
                move.po_tds_tax_id = False
                move.po_tds_section = False

    def action_view_purchase_tds(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Purchase TDS'),
            'res_model': 'purchase.tds',
            'view_mode': 'list,form',
            'domain': [('bill_id', '=', self.id)],
            'context': {
                'default_bill_id': self.id,
            },
        }
        if len(self.purchase_tds_ids) == 1:
            form_view = self.env.ref('purchase_tds.view_purchase_tds_form', raise_if_not_found=False)
            action['views'] = [(form_view.id, 'form')] if form_view else [(False, 'form')]
            action['res_id'] = self.purchase_tds_ids.id
        return action
