# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date


class MOPMaster(models.Model):
    _name = 'mop.master'
    _description = 'MOP Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'effective_date desc, product_id'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='SKU', required=True, index=True,
                                 domain=[('type', '!=', 'service')], tracking=True)
    sku_code = fields.Char(string='SKU Code', related='product_id.default_code', store=True, readonly=True)
    mop = fields.Float(string='MOP', digits='Product Price', required=True,
                       help='Market Operating Price', tracking=True)
    effective_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today,
        tracking=True,
        help='Effective date of Market Operating Price for this SKU. Back date and future date are allowed.',
    )
    active = fields.Boolean(string='Active', default=True, tracking=True)

    _sql_constraints = [
        ('unique_product_effective_date', 'unique(product_id, effective_date)',
         'A MOP record already exists for this product with the same effective date!'),
    ]

    @api.model
    def get_current_mop(self, product_id, date=None):
        """Get the current MOP for a product based on effective date"""
        if not date:
            date = fields.Date.today()

        mop_record = self.search([
            ('product_id', '=', product_id),
            ('effective_date', '<=', date),
            ('active', '=', True)
        ], order='effective_date desc', limit=1)

        return mop_record.mop if mop_record else False

