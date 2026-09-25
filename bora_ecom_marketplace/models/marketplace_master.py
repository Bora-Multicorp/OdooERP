# -*- coding: utf-8 -*-
from odoo import fields, models


class BoraMarketplaceMaster(models.Model):
    _name = 'bora.marketplace.master'
    _description = 'Marketplace Master'
    _order = 'sequence, name'

    name = fields.Char(
        string='Marketplace Name',
        required=True,
        translate=True,
        index=True,
        help="Marketplace name, e.g., Amazon, Flipkart.",
    )
    code = fields.Char(
        string='Code',
        index=True,
        help="Technical or short identifier for the marketplace.",
    )
    description = fields.Text(
        string='Description',
        help="Optional notes or details regarding this marketplace.",
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display ordering.",
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Set to false to hide this marketplace without deleting it.",
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The Marketplace name must be unique!'),
    ]
