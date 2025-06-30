# -*- coding: utf-8 -*-

from odoo import api, fields, models

class RejectRequestWizard(models.TransientModel):
    _name = 'reject.request.wizard'
    _description = 'Reject Request Form'

    approval_user_id = fields.Many2one('approval.users', string='Approval User', domain="[('id', '=', active_id)]")
    remark = fields.Char('Remark', required=True)

    def action_reject_request(self):
        if self.approval_user_id:
            # Update the approval user with the reject stage
            self.approval_user_id.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
        # Close the wizard
        return {'type': 'ir.actions.act_window_close'}
