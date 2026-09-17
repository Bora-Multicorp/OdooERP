# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    iec_no = fields.Char(
        string="IEC No",
        help="Import Export Code number (India).",
    )

    ks_sale_procurement_team_user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='ks_sale_order_company_procurement_team_rel',
        column1='company_id',
        column2='user_id',
        string='Procurement Team',
        help='Users who will receive email notifications when a product with '
             'insufficient stock is added to a sales order. '
             'The system will block the addition and notify these users.',
    )

    ks_enable_shipping_cash_charges = fields.Boolean(
        string="Enable Cash Handling & Transfer Charges",
        default=False,
        help="Enable Cash Handling Charges and Transfer Charges buttons in Sales Order for this company.",
    )
    ks_cash_handling_charge_type = fields.Selection(
        selection=[
            ('fixed', 'Fixed amount'),
            ('percentage', 'Percentage'),
        ],
        string="Cash Handling Charges Type",
        default=False,
        help="Type of Cash Handling Charges: Fixed amount or Percentage.",
    )
    ks_cash_handling_charge_value = fields.Float(
        string="Cash Handling Charges Value",
        default=False,
        help="Value for Cash Handling Charges (amount or percentage depending on type).",
    )
    ks_cash_handling_charge_pct = fields.Float(
        string="Cash Handling Charges (%)",
        default=False,
        help="Default percentage for Cash Handling Charges.",
    )
    ks_custom_cash_handling_charge_currency_id = fields.Many2one(
        'res.currency',
        string="Custom Cash Handling Charge Currency",
    )
    ks_cash_handling_charge_currency_id = fields.Many2one(
        'res.currency',
        string="Cash Handling Charge Currency",
        compute='_compute_ks_cash_handling_charge_currency_id',
        inverse='_inverse_ks_cash_handling_charge_currency_id',
        help="Currency for Cash Handling Charges Fixed Amount.",
    )
    ks_transfer_charge_amount = fields.Float(
        string="Transfer Charges Amount",
        default=False,
        help="Default flat amount for Transfer Charges.",
    )
    ks_custom_transfer_charge_currency_id = fields.Many2one(
        'res.currency',
        string="Custom Transfer Charge Currency",
    )
    ks_transfer_charge_currency_id = fields.Many2one(
        'res.currency',
        string="Transfer Charge Currency",
        compute='_compute_ks_transfer_charge_currency_id',
        inverse='_inverse_ks_transfer_charge_currency_id',
        help="Currency for Transfer Charges Flat Amount.",
    )

    @api.depends('currency_id', 'ks_custom_cash_handling_charge_currency_id')
    def _compute_ks_cash_handling_charge_currency_id(self):
        for company in self:
            company.ks_cash_handling_charge_currency_id = (
                company.ks_custom_cash_handling_charge_currency_id or company.currency_id
            )

    def _inverse_ks_cash_handling_charge_currency_id(self):
        for company in self:
            if company.ks_cash_handling_charge_currency_id == company.currency_id:
                company.ks_custom_cash_handling_charge_currency_id = False
            else:
                company.ks_custom_cash_handling_charge_currency_id = company.ks_cash_handling_charge_currency_id

    @api.depends('currency_id', 'ks_custom_transfer_charge_currency_id')
    def _compute_ks_transfer_charge_currency_id(self):
        for company in self:
            company.ks_transfer_charge_currency_id = (
                company.ks_custom_transfer_charge_currency_id or company.currency_id
            )

    def _inverse_ks_transfer_charge_currency_id(self):
        for company in self:
            if company.ks_transfer_charge_currency_id == company.currency_id:
                company.ks_custom_transfer_charge_currency_id = False
            else:
                company.ks_custom_transfer_charge_currency_id = company.ks_transfer_charge_currency_id




