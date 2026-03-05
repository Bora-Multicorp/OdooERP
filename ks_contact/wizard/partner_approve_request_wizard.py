# -*- coding: utf-8 -*-

from odoo import fields, models, _


class PartnerApproveRequestWizard(models.TransientModel):
    _name = 'partner.approve.request.wizard'
    _description = 'Partner Approve Request'

    partner_id = fields.Many2one('res.partner', string='Contact (Vendor)', required=True)
    remark = fields.Char('Remark', required=True, tracking=True)

    def action_approve_request(self):
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
        approval_line.sudo().write({
            'state': 'approve',
            'remark': self.remark,
            'action_date': fields.Datetime.now(),
        })
        partner.message_post(
            body=_("%s approved by %s - Remark: %s") % (level, current_user.name, self.remark),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        self.env['mail.activity'].search([
            ('res_model', '=', 'res.partner'),
            ('res_id', '=', partner.id),
            ('user_id', '=', current_user.id),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
        ]).unlink()
        partner._update_assigned_to_partner_approval()
        return {'type': 'ir.actions.act_window_close'}
