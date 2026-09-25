# -*- coding: utf-8 -*-
from odoo import fields, models


class BoraEcomMaster(models.Model):
    _name = 'bora.ecom.master'
    _description = 'E-Com Master'
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
        index=True,
        help="Business category name, e.g., Domestic, E-Commerce, Export.",
    )
    code = fields.Char(
        string='Code',
        index=True,
        help="Technical or short identifier for the category.",
    )
    is_ecommerce = fields.Boolean(
        string='Is E-Commerce',
        default=False,
        help="Check this if the category represents E-Commerce transactions.",
    )
    description = fields.Text(
        string='Description',
        help="Optional notes or details regarding this business category.",
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help="Display ordering.",
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help="Set to false to hide this category without deleting it.",
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The E-Com category name must be unique!'),
    ]
