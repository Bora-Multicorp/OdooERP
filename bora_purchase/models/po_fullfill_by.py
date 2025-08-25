from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    fulfillment_by = fields.Selection([
        ('vendor', 'Vendor'),
        ('bora', 'Bora'),
    ], string="Fulfillment By", required=True)