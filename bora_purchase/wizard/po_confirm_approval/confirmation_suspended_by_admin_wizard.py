# -*- coding: utf-8 -*-

from odoo import fields, models

class POSuspensionWizard(models.TransientModel):
    _name = 'suspend.po.confirm.wizard'
    _description = 'Suspend confirmation wizard'

    order_id = fields.Many2one('purchase.order', string="Suspenstion for Purchase Order Confirmation")

    remark = fields.Char('Remark', required=True)

    def action_done(self): 
        self.ensure_one()
        
        self.order_id.suspend_approval_process(self.remark)

        return {'type': 'ir.actions.act_window_close'}