# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class MOPMaster(models.Model):
    _name = 'mop.master'
    _description = 'MOP Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
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

    def _get_realme_brand_id(self):
        """Return the Realme brand id (from data record). Used to restrict MOP to Realme products only."""
        brand = self.env.ref('ks_product_master.brand_realme', raise_if_not_found=False)
        return brand.id if brand else -1

    def _check_product_brand_realme(self):
        """Only products with Realme brand can be used in MOP."""
        realme_id = self._get_realme_brand_id()
        if realme_id <= 0:
            return
        for rec in self:
            if rec.product_id and rec.product_id.product_tmpl_id.brand_id.id != realme_id:
                raise ValidationError(_(
                    'Only products with brand "Realme" can be used in MOP. '
                    'Product "%s" has brand "%s".'
                ) % (rec.product_id.display_name, rec.product_id.product_tmpl_id.brand_id.name or ''))

    def write(self, vals):
        """Validate Realme brand when product_id is set; prevent editing past effective dates; chatter."""
        if vals.get('product_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            realme_id = self._get_realme_brand_id()
            if realme_id > 0 and product.exists() and product.product_tmpl_id.brand_id.id != realme_id:
                raise ValidationError(_(
                    'Only products with brand "Realme" can be used in MOP. '
                    'Product "%s" has brand "%s".'
                ) % (product.display_name, product.product_tmpl_id.brand_id.name or ''))
        if 'effective_date' in vals or 'mop' in vals:
            today = date.today()
            for record in self:
                if record.effective_date and record.effective_date < today:
                    raise ValidationError(_(
                        'Cannot modify MOP records with past effective dates. '
                        'Please create a new MOP record with today\'s date or a future date.'
                    ))
                new_date = vals.get('effective_date', record.effective_date)
                if new_date and new_date < today:
                    raise ValidationError(_(
                        'Effective date should always be present date or future date. '
                        'No changes can be applied on MOP of past sales data.'
                    ))
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
        for vals in vals_list:
            if vals.get('product_id'):
                product = self.env['product.product'].browse(vals['product_id'])
                if product.exists():
                    realme_id = self._get_realme_brand_id()
                    if realme_id > 0 and product.product_tmpl_id.brand_id.id != realme_id:
                        raise ValidationError(_(
                            'Only products with brand "Realme" can be used in MOP. '
                            'Product "%s" has brand "%s".'
                        ) % (product.display_name, product.product_tmpl_id.brand_id.name or ''))
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

