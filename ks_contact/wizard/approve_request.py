# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ApproveRequestWizard(models.TransientModel):
    _name = 'approve.request.wizard'
    _description = 'Approve Request Form'

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="Approval for", domain="[('id', '=', active_id)]",tracking=True)
    remark = fields.Char('Remark', required=True,tracking=True)

    def action_approve_request(self):
        self.ensure_one()
        approval = self.kyc_approval_id
        current_user = self.env.user

        # Find the matching approval line for the current user (parallel approval - any pending approver can act)
        approval_line = approval.approval_users_ids.filtered(
            lambda l: l.user_id == current_user and not l.state
        )

        if approval_line:
            # Determine approval level based on sequence
            approval_level = "Approval Level 1" if approval_line.sequence == 1 else "Approval Level 2"
            
            approval_line.sudo().write({
                'state': 'approve',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            
            # Post chatter message with approval level information
            approval.message_post(
                body=_("%s approved by %s -Remark:- %s") % (
                    approval_level,
                    current_user.name,
                    self.remark
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            # Update assigned_to for backward compatibility (next pending approver)
            approval.sudo()._update_assigned_to()

        return {'type': 'ir.actions.act_window_close'}

