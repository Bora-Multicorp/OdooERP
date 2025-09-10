# -*- coding: utf-8 -*-

from odoo import fields, models

class SOUnlockSuspensionWizard(models.TransientModel):
    _name = 'suspend.so.unlock.wizard'
    _description = 'Suspend unlock wizard'

    order_id = fields.Many2one('sale.order', string="Suspenstion for Purchase Order Unlock")

    remark = fields.Char('Remark', required=True)

    def action_done(self): 
        self.ensure_one()

        self.order_id.suspend_unlock_process(self.remark)

        return {'type': 'ir.actions.act_window_close'}