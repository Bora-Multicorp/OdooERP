# -*- coding: utf-8 -*-
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_template_id = fields.Many2one(
        string="Product Template",
        comodel_name='product.template',
        compute='_compute_product_template_id',
        readonly=False,
        search='_search_product_template_id',
        domain=[('purchase_ok', '=', True)]
    )

    is_configurable_product = fields.Boolean(
        string="Is the product configurable?",
        related='product_template_id.has_configurable_attributes',
        depends=['product_template_id']
    )

    product_template_attribute_value_ids = fields.Many2many(
        related='product_id.product_template_attribute_value_ids',
        readonly=True
    )

    product_no_variant_attribute_value_ids = fields.Many2many(
        comodel_name='product.template.attribute.value',
        string='Product attribute values that do not create variants',
        ondelete='restrict'
    )

    product_custom_attribute_value_ids = fields.One2many(
        comodel_name='product.attribute.custom.value',
        inverse_name='purchase_order_line_id',
        string='Custom Values',
        copy=True
    )

    @api.depends('product_id')
    def _compute_product_template_id(self):
        for line in self:
            line.product_template_id = line.product_id.product_tmpl_id

    def _search_product_template_id(self, operator, value):
        return [('product_id.product_tmpl_id', operator, value)]

    def _get_product_purchase_description(self, product_lang):
        name = super()._get_product_purchase_description(product_lang)
        for no_variant_attribute_value in self.product_no_variant_attribute_value_ids:
            name += f"\n{no_variant_attribute_value.attribute_id.name}: {no_variant_attribute_value.name}"
        for custom_attribute_value in self.product_custom_attribute_value_ids:
            name += f"\n{custom_attribute_value.custom_product_template_attribute_value_id.attribute_id.name}: {custom_attribute_value.custom_value}"
        return name
