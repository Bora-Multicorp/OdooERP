# -*- coding: utf-8 -*-

from markupsafe import Markup
from odoo import fields, models, _


class PartnerRejectRequestWizard(models.TransientModel):
    _name = 'partner.reject.request.wizard'
    _description = 'Partner Reject Request'

    partner_id = fields.Many2one('res.partner', string='Contact (Vendor)', required=True)
    remark = fields.Char('Remark', required=True, tracking=True)

    def action_reject_request(self):
        self.ensure_one()
        partner = self.partner_id
        current_user = self.env.user

        pending = sorted(
            partner.approval_line_ids.filtered(lambda l: l.is_active and not l.state),
            key=lambda l: l.sequence
        )
        if not pending or pending[0].user_id.id != current_user.id:
            return {'type': 'ir.actions.act_window_close'}

        approval_line = pending[0]
        level = _("Approver 1") if approval_line.sequence == 1 else _("Approver 2")
        approval_line.write({
            'state': 'reject',
            'remark': self.remark,
            'action_date': fields.Datetime.now(),
        })
        partner.message_post(
            body=Markup(_("%s rejected by %s (%s). Reason: %s") % (
                level, current_user.name, current_user.login, self.remark
            )),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        # Suspend remaining pending lines
        still_pending = partner.approval_line_ids.filtered(lambda l: l.is_active and not l.state)
        if still_pending:
            still_pending.write({
                'state': 'suspended',
                'remark': _("Rejected by %s (%s)") % (current_user.name, level),
                'action_date': fields.Datetime.now(),
            })
        partner.sudo().write({
            'approval_status': 'draft',
            'rejection_date': fields.Datetime.now(),
            'rejection_reason': self.remark,
            'is_rejected': True,
        })
        self.env['mail.activity'].search([
            ('res_model', '=', 'res.partner'),
            ('res_id', '=', partner.id),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
        ]).unlink()
        return {'type': 'ir.actions.act_window_close'}
