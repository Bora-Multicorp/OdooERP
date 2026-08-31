from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_template_id = fields.Many2one(
        comodel_name='product.template',
        string='Product',
        related='product_id.product_tmpl_id',
        store=True,
        readonly=False,
        domain=[('purchase_ok', '=', True)],
    )
    is_configurable_product = fields.Boolean(
        string='Is the product configurable?',
        related='product_template_id.has_configurable_attributes',
        depends=['product_template_id'],
    )
    product_template_attribute_value_ids = fields.Many2many(
        related='product_id.product_template_attribute_value_ids',
        depends=['product_id'],
    )
    product_custom_attribute_value_ids = fields.One2many(
        comodel_name='product.attribute.custom.value',
        inverse_name='purchase_order_line_id',
        string='Custom values',
        compute='_compute_custom_attribute_values',
        store=True,
        readonly=False,
        precompute=True,
        copy=True,
    )
    product_no_variant_attribute_value_ids = fields.Many2many(
        comodel_name='product.template.attribute.value',
        string='Extra Values',
        compute='_compute_no_variant_attribute_values',
        store=True,
        readonly=False,
        precompute=True,
        ondelete='restrict',
    )

    @api.depends('product_id')
    def _compute_custom_attribute_values(self):
        for line in self:
            if line.product_id and not line.product_custom_attribute_value_ids:
                continue
            line.product_custom_attribute_value_ids = self.env['product.attribute.custom.value'].search([
                ('purchase_order_line_id', '=', line.id)
            ])

    @api.depends('product_id')
    def _compute_no_variant_attribute_values(self):
        for line in self:
            if not line.product_id:
                line.product_no_variant_attribute_value_ids = [(5, 0, 0)]
                continue
            attrs = line.product_id.product_template_attribute_value_ids.filtered(
                lambda ptav: ptav.attribute_id.create_variant == 'no_variant'
            )
            line.product_no_variant_attribute_value_ids = attrs
