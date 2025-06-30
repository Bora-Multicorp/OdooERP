# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ApproveRequestWizard(models.TransientModel):
    _name = 'approve.request.wizard'
    _description = 'Approve Request Form'

    approval_user_id = fields.Many2one('approval.users', string='Approval Users', domain="[('id', '=', active_id)]")
    remark = fields.Char('Remark', required=True)


    def action_approve_request(self):
        # Check if there is an approval user to update
        if self.approval_detail_id:
            # Update the approval user with the approve stage
            self.approval_detail_id.write({
                'state': 'approve',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
        # Close the wizard
        return {'type': 'ir.actions.act_window_close'}
