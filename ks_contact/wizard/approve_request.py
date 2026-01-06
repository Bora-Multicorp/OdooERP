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

        # Find the matching approval line for the current user (sequential approval - only current approver can act)
        # Get the first pending approver in sequence
        pending_approvers = sorted(
            approval.approval_users_ids.filtered(lambda l: not l.state),
            key=lambda l: l.sequence
        )
        
        # Only allow approval if current user is the first pending approver
        approval_line = None
        if pending_approvers and pending_approvers[0].user_id == current_user:
            approval_line = pending_approvers[0]

        if approval_line:
            # Determine approval level based on sequence
            approval_level = "Approver 1" if approval_line.sequence == 1 else "Approver 2"
            
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
            
            # Remove activity for current approver
            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'res.partner.kyc.approval'),
                ('res_id', '=', approval.id),
                ('user_id', '=', current_user.id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ])
            activities.unlink()
            
            # Update assigned_to and trigger next approver activity (sequential approval)
            approval.sudo()._update_assigned_to()

        return {'type': 'ir.actions.act_window_close'}

