# -*- coding: utf-8 -*-

from odoo import fields, models

class POSuspensionWizard(models.TransientModel):
    _name = 'suspend.vendor.confirm.wizard'
    _description = 'Suspend confirmation wizard'

    kyc_id = fields.Many2one('res.partner.kyc.approval', string="Suspenstion for Vendor Kyc Confirmation")

    remark = fields.Char('Remark', required=True)

    def action_done(self): 
        self.ensure_one()

        self.kyc_id.suspend_approval_process(self.remark)

        return {'type': 'ir.actions.act_window_close'}