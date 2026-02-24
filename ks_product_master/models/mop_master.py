# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class MOPMaster(models.Model):
    _name = 'mop.master'
    _description = 'MOP Master'
    _order = 'effective_date desc, product_id'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='SKU', required=True, index=True, 
                                 domain=[('type', '!=', 'service')])
    sku_code = fields.Char(string='SKU Code', related='product_id.default_code', store=True, readonly=True)
    mop = fields.Float(string='MOP', digits='Product Price', required=True, 
                       help='Market Operating Price')
    effective_date = fields.Date(string='Effective Date', required=True, default=fields.Date.today,
                                  help='Effective date of Market Operating Price of that SKU. '
                                       'Please note, effective date should always be present date or future date, '
                                       'no changes can be applied on MOP of past sales data.')
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
        ('unique_product_effective_date', 'unique(product_id, effective_date)',
         'A MOP record already exists for this product with the same effective date!'),
    ]

    @api.constrains('effective_date')
    def _check_effective_date(self):
        """Validate that effective date is today or future date"""
        today = date.today()
        for record in self:
            if record.effective_date and record.effective_date < today:
                raise ValidationError(_(
                    'Effective date should always be present date or future date. '
                    'No changes can be applied on MOP of past sales data. '
                    'Please select today\'s date or a future date.'
                ))

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

    def write(self, vals):
        """Prevent editing MOP records with past effective dates"""
        if 'effective_date' in vals or 'mop' in vals:
            today = date.today()
            for record in self:
                # Check if existing effective date is in the past
                if record.effective_date and record.effective_date < today:
                    raise ValidationError(_(
                        'Cannot modify MOP records with past effective dates. '
                        'Please create a new MOP record with today\'s date or a future date.'
                    ))
                # Check if new effective date is in the past
                new_date = vals.get('effective_date', record.effective_date)
                if new_date and new_date < today:
                    raise ValidationError(_(
                        'Effective date should always be present date or future date. '
                        'No changes can be applied on MOP of past sales data.'
                    ))
        return super().write(vals)

