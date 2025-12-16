# your_module/models/product_category.py
from odoo import fields, models
from odoo import models, fields


class ProductCategory(models.Model):
    _inherit = 'product.category'

    product_attributes = fields.Many2many('product.attribute', 
                                          'product_category_attribute_rel',  # name of the relation table
                                          'category_id',                     # column that links to product.category
                                          'attribute_id',                    # column that links to product.attribute
    )