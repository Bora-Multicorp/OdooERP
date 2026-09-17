# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_id = fields.Many2one(
        related='company_id.currency_id',
        readonly=True,
    )
    ks_sale_procurement_team_user_ids = fields.Many2many(
        related='company_id.ks_sale_procurement_team_user_ids',
        readonly=False,
        string='Procurement Team',
        help='Users who will receive email notifications when a product with '
             'insufficient stock is added to a sales order. '
             'The system will block the addition and notify these users.',
    )
    ks_enable_shipping_cash_charges = fields.Boolean(
        related='company_id.ks_enable_shipping_cash_charges',
        readonly=False,
        string="Enable Cash Handling & Transfer Charges",
    )
    ks_cash_handling_charge_type = fields.Selection(
        related='company_id.ks_cash_handling_charge_type',
        readonly=False,
        string="Cash Handling Charges Type",
    )
    ks_cash_handling_charge_value = fields.Float(
        related='company_id.ks_cash_handling_charge_value',
        readonly=False,
        string="Cash Handling Charges Value",
    )
    ks_cash_handling_charge_pct = fields.Float(
        related='company_id.ks_cash_handling_charge_pct',
        readonly=False,
        string="Cash Handling Charges (%)",
    )
    ks_cash_handling_charge_currency_id = fields.Many2one(
        related='company_id.ks_cash_handling_charge_currency_id',
        readonly=False,
        string="Cash Handling Charge Currency",
    )
    ks_transfer_charge_amount = fields.Float(
        related='company_id.ks_transfer_charge_amount',
        readonly=False,
        string="Transfer Charges Amount",
    )
    ks_transfer_charge_currency_id = fields.Many2one(
        related='company_id.ks_transfer_charge_currency_id',
        readonly=False,
        string="Transfer Charge Currency",
    )




