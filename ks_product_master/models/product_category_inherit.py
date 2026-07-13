from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    product_attributes = fields.Many2many('product.attribute',
                                          'product_category_attribute_rel',  # name of the relation table
                                          'category_id',                     # column that links to product.category
                                          'attribute_id',                    # column that links to product.attribute
                                          )

    is_mobile_category = fields.Boolean(
        string="Is Mobile Category",
        help="Check this if products under this category (or its sub-categories) "
             "should be treated as mobile phones, enabling IMEI tracking on stock moves."
    )