# -*- coding: utf-8 -*-
from odoo import api, fields, models
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
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase TDS',
            'res_model': 'purchase.tds',
            'view_mode': 'list,form',
            'domain': [('purchase_id', '=', self.id)],
            'context': {
                'default_purchase_id': self.id,
            },
        }

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
