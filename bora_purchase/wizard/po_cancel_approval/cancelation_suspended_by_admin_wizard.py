# -*- coding: utf-8 -*-

from odoo import fields, models

class POCancelationSuspensionWizard(models.TransientModel):
    _name = 'suspend.po.cancelation.wizard'
    _description = 'Suspend cnacelation wizard'

    order_id = fields.Many2one('purchase.order', string="Suspenstion for Purchase Order Cancelation")

    remark = fields.Char('Remark', required=True)

    def action_done(self): 
        self.ensure_one()

        self.order_id.suspend_cancelation_process(self.remark)

        return {'type': 'ir.actions.act_window_close'}