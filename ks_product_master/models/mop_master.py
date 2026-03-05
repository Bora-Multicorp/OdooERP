# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
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

    def write(self, vals):
        """Post a message to chatter when tracked fields are modified."""
        res = super().write(vals)
        if vals and res:
            tracked_labels = []
            for key in vals:
                if key in self._fields and key != 'message_main_attachment_id':
                    field = self._fields[key]
                    label = getattr(field, 'string', key)
                    if key == 'product_id':
                        new_product = self.env['product.product'].browse(vals.get(key)).exists()
                        new_name = new_product.display_name if new_product else str(vals.get(key))
                        tracked_labels.append(_('%s: %s') % (label, new_name))
                    elif key == 'mop':
                        tracked_labels.append(_('%s: %s') % (label, vals[key]))
                    elif key == 'effective_date':
                        tracked_labels.append(_('%s: %s') % (label, vals[key]))
                    elif key == 'active':
                        tracked_labels.append(_('%s: %s') % (label, _('Yes') if vals[key] else _('No')))
                    else:
                        tracked_labels.append(_('%s: %s') % (label, vals[key]))
            if tracked_labels:
                for record in self:
                    record.message_post(
                        body=_('MOP Master updated: %s') % ', '.join(tracked_labels),
                        message_type='notification',
                    )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record.message_post(
                body=_('MOP Master record created: SKU %s, MOP %s, Effective Date %s') % (
                    record.product_id.display_name,
                    record.mop,
                    record.effective_date,
                ),
                message_type='notification',
            )
        return records

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

