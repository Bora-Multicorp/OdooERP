# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import api, fields, models, _


class RejectRequestWizard(models.TransientModel):
    _name = 'reject.request.wizard'
    _description = 'Reject Request Form'

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="Approval for Vendor",
                                      domain="[('id', '=', active_id)]",tracking=True)
    remark = fields.Char('Remark', required=True,tracking=True)

    def action_reject_request(self):
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
            
            approval_line.write({
                'state': 'reject',
                'remark': self.remark,
                'action_date': fields.Datetime.now(),
            })
            
            # Post chatter message with rejection level information
            approval.message_post(
                body=Markup(_("%s rejected by %s (%s). Reason: %s") % (
                    approval_level,
                    current_user.name,
                    current_user.login,
                    self.remark
                )),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            approval.write({
                'rejection_date': fields.Datetime.now(),
                'rejection_reason': self.remark,
                'assigned_to': False,
                'is_rejected': True
            })
            approval.partner_id.sudo().write({
                'rejection_date': fields.Datetime.now(),
                'rejection_reason': self.remark,
                'is_rejected': True
            })
            
            # Suspend all other pending approvals (any rejection = rejected)
            pending_users_lines = approval.approval_users_ids.filtered(
                lambda l: not l.state
            )

            if pending_users_lines:
                pending_users_lines.write({
                    'state': 'suspended',
                    'remark': _("Rejected by %s (%s)") % (current_user.name, approval_level),
                    'action_date': fields.Datetime.now(),
                })
                
                # Remove activities for all pending approvers
                activities = self.env['mail.activity'].search([
                    ('res_model', '=', 'res.partner.kyc.approval'),
                    ('res_id', '=', approval.id),
                    ('user_id', 'in', pending_users_lines.mapped('user_id').ids),
                    ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ])
                activities.unlink()
            
            # Remove activity for rejecting user
            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'res.partner.kyc.approval'),
                ('res_id', '=', approval.id),
                ('user_id', '=', current_user.id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ])
            activities.unlink()
            
        approval._send_notification_on_rejection()

        return {'type': 'ir.actions.act_window_close'}

