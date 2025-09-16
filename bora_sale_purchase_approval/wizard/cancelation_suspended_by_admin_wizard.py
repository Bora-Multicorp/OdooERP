# -*- coding: utf-8 -*-

from odoo import fields, models

class SOCancelationSuspensionWizard(models.TransientModel):
    _name = 'suspend.so.cancelation.wizard'
    _description = 'Suspend cnacelation wizard'

    sale_id = fields.Many2one('sale.order', string="Suspenstion for Sale Order Cancelation")

    remark = fields.Char('Remark', required=True)

    def action_done(self): 
        self.ensure_one()

        self.sale_id.suspend_so_cancelation_process(self.remark)

        return {'type': 'ir.actions.act_window_close'}