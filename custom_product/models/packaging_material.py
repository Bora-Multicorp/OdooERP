from odoo import models, fields

class PackingMaterialLine(models.Model):
    _name = 'packing.material.line'
    _description = 'Packing Material Rule Line'

    product_tmpl_id = fields.Many2one(
        'product.template', required=True, ondelete='cascade', string="Product Template"
    )
    packing_material_id = fields.Many2one(
        'product.product', required=True, string="Packing Material"
    )
    carton_type = fields.Selection([
        ('loose', 'Loose Carton'),
        ('master', 'Master Carton')
    ], string="Carton Type", required=True)

    qty_per_unit = fields.Float(string="Qty per Unit/Kg", required=True, default=1.0)

    apply_by = fields.Selection([
        ('unit', 'Per Unit'),
        ('weight', 'Per Kg')
    ], default='unit', string="Apply Based On")

    box_type = fields.Selection([
        ('regular', 'Regular Box'),
        ('large', 'Large Box'),
        ('xlarge', 'XLarge Box')
    ], string="Box Type")
