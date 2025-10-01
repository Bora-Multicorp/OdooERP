# -*- coding: utf-8 -*-

from odoo import fields, models

class SOSuspensionWizard(models.TransientModel):
    _name = 'suspend.so.confirm.wizard'
    _description = 'Suspend confirmation wizard'

    sale_id = fields.Many2one('sale.order', string="Suspenstion for Sale Order Confirmation")

    remark = fields.Char('Remark', required=True)

    def action_done(self): 
        self.ensure_one()

        self.sale_id.suspend_approval_process(self.remark)

        return {'type': 'ir.actions.act_window_close'}