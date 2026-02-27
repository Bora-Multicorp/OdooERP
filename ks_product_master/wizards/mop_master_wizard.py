# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MOPMasterWizard(models.TransientModel):
    _name = 'mop.master.wizard'
    _description = 'Create MOP Records'

    effective_date = fields.Date(
        string='Effective Date',
        required=True,
        default=fields.Date.today,
        help='Back date and future date are allowed.',
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        help='Leave empty to create MOP for all storable products, or select specific products.',
        domain=[('type', '!=', 'service')],
    )
    category_id = fields.Many2one('product.category', string='Category')
    brand_id = fields.Many2one('product.brand', string='Brand', help='Optional filter by brand.')
    default_mop = fields.Float(
        string='Default MOP',
        digits='Product Price',
        default=0.0,
        help='Default MOP value when product has no list price. Otherwise list price is used.',
    )

    def action_create_mop(self):
        self.ensure_one()
        Product = self.env['product.product']
        MOPMaster = self.env['mop.master']

        if self.product_ids:
            products = self.product_ids
        else:
            domain = [('type', '!=', 'service')]
            if self.category_id:
                domain.append(('categ_id', 'child_of', self.category_id.id))
            if self.brand_id:
                domain.append(('brand_id', '=', self.brand_id.id))
            products = Product.search(domain)

        if not products:
            raise UserError(_('No products found. Select products or adjust filters.'))

        created = 0
        for product in products:
            existing = MOPMaster.search([
                ('product_id', '=', product.id),
                ('effective_date', '=', self.effective_date),
            ], limit=1)
            if existing:
                continue
            mop_value = product.list_price if product.list_price else self.default_mop
            if hasattr(product, 'mop') and product.mop:
                mop_value = product.mop
            elif hasattr(product, 'product_tmpl_id') and hasattr(product.product_tmpl_id, 'mop') and product.product_tmpl_id.mop:
                mop_value = product.product_tmpl_id.mop
            MOPMaster.create({
                'product_id': product.id,
                'effective_date': self.effective_date,
                'mop': mop_value,
                'active': True,
            })
            created += 1

        return {
            'type': 'ir.actions.act_window',
            'name': _('MOP Master'),
            'res_model': 'mop.master',
            'view_mode': 'list,form',
            'domain': [('effective_date', '=', self.effective_date)],
            'context': {'search_default_active': 1},
        }
