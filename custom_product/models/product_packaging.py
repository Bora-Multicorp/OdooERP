from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    packing_material_line_ids = fields.One2many(
        'packing.material.line', 'product_tmpl_id', string="Packing Materials"
    )
    is_packaging = fields.Boolean(
        string="Is Packaging Material", compute="_compute_is_packaging_material", store=True
    )

    @api.depends('categ_id')
    def _compute_is_packaging_material(self):
        for rec in self:
            rec.is_packaging = rec.categ_id.name == 'Packaging Material'

