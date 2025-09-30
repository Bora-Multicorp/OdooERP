from odoo import models, fields

class DeliveryPartners(models.Model):
    _name = 'delivery.partners'
    _description = 'Delivery Partners'

    name = fields.Char(string='Name', required=True)
