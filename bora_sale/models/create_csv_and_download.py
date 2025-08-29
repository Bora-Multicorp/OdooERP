from odoo import models, fields

class StockMove(models.Model):
    _inherit = "stock.move"

    download_url = fields.Char("Download URL")
