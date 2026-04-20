from odoo import models


class ResPartner(models.Model):
    _inherit = ["multi.company.abstract", "res.partner"]
    _name = "res.partner"
