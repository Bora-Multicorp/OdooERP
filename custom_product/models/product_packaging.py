from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    packing_material_line_ids = fields.One2many(
        'packing.material.line', 'product_tmpl_id', string="Packing Materials"
    )


