# -*- coding: utf-8 -*-

from odoo import fields, models


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
    ks_transfer_charge_amount = fields.Float(
        string="Transfer Charges Amount",
        default=False,
        help="Default flat amount for Transfer Charges.",
    )


