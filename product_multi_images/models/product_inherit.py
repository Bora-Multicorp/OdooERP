from odoo import models, fields, api

class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'

    name = fields.Char(string="Brand", required=True)
    description = fields.Text(string="Description")


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('product.brand', string="Brand")
    image_1 = fields.Image("Image 1")
    image_2 = fields.Image("Image 2")
    image_3 = fields.Image("Image 3")
    image_4 = fields.Image("Image 4")
    image_5 = fields.Image("Image 5")
