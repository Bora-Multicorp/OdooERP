from odoo import fields, models, api

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    backdate_po = fields.Datetime('Order Date')