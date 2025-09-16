from odoo import fields, models, api

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    date_approve = fields.Datetime('Create Date')


    def button_approve(self, force=False):
        self = self.filtered(lambda order: order._approval_allowed())
        self.write({'state': 'purchase'})
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}

    def write(self, vals):
        print("--------- in WRITE =>", vals)
        return super().write(vals)