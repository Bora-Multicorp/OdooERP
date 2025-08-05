from odoo import fields, models

class SaleOrderUnlock(models.Model):
    _inherit = 'sale.order'

    def action_unlock(self):
        print('Unlock button pressed')
