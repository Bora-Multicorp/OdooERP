# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BoraCreditNoteApprovalRequestWizard(models.TransientModel):
    _name = 'bora.credit.note.approval.request.wizard'
    _description = 'Bora Credit Note Approval Request Wizard'

    bora_cn_move_id = fields.Many2one('account.move', string='Credit Note', required=True)

    bora_cn_approver1_user_ids = fields.Many2many(
        'res.users', compute='_compute_approver_user_ids', store=False,
        relation='bora_cn_req_wiz_approver1_rel')
    bora_cn_approver2_user_ids = fields.Many2many(
        'res.users', compute='_compute_approver_user_ids', store=False,
        relation='bora_cn_req_wiz_approver2_rel')
    bora_cn_approver1_filtered_ids = fields.Many2many(
        'res.users', compute='_compute_filtered_approver_ids', store=False,
        relation='bora_cn_req_wiz_filtered1_rel')
    bora_cn_approver2_filtered_ids = fields.Many2many(
        'res.users', compute='_compute_filtered_approver_ids', store=False,
        relation='bora_cn_req_wiz_filtered2_rel')

    bora_cn_approver1_user = fields.Many2one(
        'res.users', string='Approver 1', required=True,
        domain="[('id', 'in', bora_cn_approver1_filtered_ids)]")
    bora_cn_approver2_user = fields.Many2one(
        'res.users', string='Approver 2',
        domain="[('id', 'in', bora_cn_approver2_filtered_ids)]")
    bora_cn_reason = fields.Text(string='Reason', placeholder='Optional reason for this request...')
    bora_cn_show_approver2 = fields.Boolean(compute='_compute_show_approver2')
    bora_cn_approval_info = fields.Html(compute='_compute_approval_info', readonly=True)
    bora_cn_is_update_mode = fields.Boolean(string='Is Update Mode', default=False)
    bora_cn_pm1_already_approved = fields.Boolean(string='PM1 Already Approved', default=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        is_update = self.env.context.get('bora_cn_is_update', False)
        move_id = self.env.context.get('default_bora_cn_move_id') or res.get('bora_cn_move_id')
        if is_update and move_id:
            move = self.env['account.move'].browse(move_id)
            if move.bora_cn_pm1_approved and move.bora_cn_pm1_id:
                res['bora_cn_pm1_already_approved'] = True
                res['bora_cn_approver1_user'] = move.bora_cn_pm1_id.id
        return res

    @api.depends('bora_cn_move_id')
    def _compute_show_approver2(self):
        for wiz in self:
            if wiz.bora_cn_move_id._has_cn_approval_config():
                wiz.bora_cn_show_approver2 = (
                    wiz.bora_cn_move_id._get_cn_approval_config().is_dual_approval()
                )
            else:
                wiz.bora_cn_show_approver2 = False

    @api.depends('bora_cn_move_id')
    def _compute_approver_user_ids(self):
        for wiz in self:
            if wiz.bora_cn_move_id._has_cn_approval_config():
                config = wiz.bora_cn_move_id._get_cn_approval_config()
                wiz.bora_cn_approver1_user_ids = config.bora_cn_pm1_ids
                wiz.bora_cn_approver2_user_ids = config.bora_cn_pm2_ids
            else:
                wiz.bora_cn_approver1_user_ids = False
                wiz.bora_cn_approver2_user_ids = False

    @api.depends('bora_cn_approver1_user_ids', 'bora_cn_approver2_user_ids',
                 'bora_cn_approver1_user', 'bora_cn_approver2_user')
    def _compute_filtered_approver_ids(self):
        for wiz in self:
            wiz.bora_cn_approver1_filtered_ids = (
                wiz.bora_cn_approver1_user_ids - wiz.bora_cn_approver2_user
                if wiz.bora_cn_approver2_user else wiz.bora_cn_approver1_user_ids
            )
            wiz.bora_cn_approver2_filtered_ids = (
                wiz.bora_cn_approver2_user_ids - wiz.bora_cn_approver1_user
                if wiz.bora_cn_approver1_user else wiz.bora_cn_approver2_user_ids
            )

    @api.depends('bora_cn_move_id', 'bora_cn_approver1_user',
                 'bora_cn_approver2_user', 'bora_cn_is_update_mode')
    def _compute_approval_info(self):
        for wiz in self:
            if not wiz.bora_cn_move_id._has_cn_approval_config():
                wiz.bora_cn_approval_info = '<p>No credit note approval configuration found.</p>'
                continue
            config = wiz.bora_cn_move_id._get_cn_approval_config()
            move = wiz.bora_cn_move_id
            html = ''

            if wiz.bora_cn_is_update_mode and move.bora_cn_pm1_approved and move.bora_cn_pm1_id:
                html += (
                    '<div class="alert alert-success" role="alert">'
                    '<strong>&#10003; Approver 1 (%s) has already approved this request.</strong>'
                    ' Keeping the same Approver 1 will preserve their approval.'
                    '</div>'
                ) % move.bora_cn_pm1_id.name

            html += '<div class="alert alert-info">'
            html += '<h5><strong>Credit Note Approval Request</strong></h5>'
            html += '<p>You are about to submit this credit note for approval before confirmation.</p>'
            if config.is_dual_approval():
                html += ('<p><strong>Note:</strong> Both Approver 1 and Approver 2 approval is required. '
                         'Approver 2 cannot approve until Approver 1 has approved.</p>')
            else:
                html += '<p><strong>Note:</strong> Approver 1 approval is required.</p>'
            html += '</div>'
            wiz.bora_cn_approval_info = html

    @api.onchange('bora_cn_approver1_user')
    def _onchange_approver1(self):
        if self.bora_cn_approver1_user and self.bora_cn_approver2_user == self.bora_cn_approver1_user:
            self.bora_cn_approver2_user = False

    @api.onchange('bora_cn_approver2_user')
    def _onchange_approver2(self):
        if self.bora_cn_approver2_user and self.bora_cn_approver1_user == self.bora_cn_approver2_user:
            self.bora_cn_approver1_user = False

    def action_confirm_request(self):
        self.ensure_one()
        if not self.bora_cn_approver1_user:
            raise UserError(_('Please select Approver 1.'))
        if self.bora_cn_show_approver2 and not self.bora_cn_approver2_user:
            raise UserError(_('Please select Approver 2 (required for dual approval mode).'))

        is_update = self.env.context.get('bora_cn_is_update', False)
        move = self.bora_cn_move_id

        if is_update and move.bora_cn_pm1_approved and move.bora_cn_pm1_id:
            if move.bora_cn_pm1_id != self.bora_cn_approver1_user:
                raise UserError(_(
                    "Approver 1 (%s) has already approved this request and cannot be changed."
                ) % move.bora_cn_pm1_id.name)

        # If PM1 is unchanged and already approved, preserve their approval
        preserve_pm1 = (
            is_update
            and move.bora_cn_pm1_id
            and move.bora_cn_pm1_id == self.bora_cn_approver1_user
            and move.bora_cn_pm1_approved
        )

        if is_update:
            move._bora_cancel_cn_activities()
            write_vals = {
                'bora_cn_pm1_id': False,
                'bora_cn_pm2_id': False,
                'bora_cn_pm2_approved': False,
            }
            if not preserve_pm1:
                write_vals['bora_cn_pm1_approved'] = False
            move.write(write_vals)
            msg = (
                _('Approval request updated by %s. Approver 1 (%s) approval preserved; only Approver 2 updated.')
                % (self.env.user.name, move.bora_cn_pm1_id.name)
                if preserve_pm1
                else _('Approval request updated by %s. Previous approvers cancelled.') % self.env.user.name
            )
            move.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')
            pre_state = move.bora_cn_pre_approval_state or 'draft'
            move.write({'state': pre_state})

        move.bora_cn_do_request_approval(
            pm1_user=self.bora_cn_approver1_user,
            pm2_user=self.bora_cn_approver2_user if self.bora_cn_approver2_user else None,
            reason=self.bora_cn_reason,
        )

        if preserve_pm1:
            move.write({'bora_cn_pm1_approved': True})
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', move.id),
                ('user_id', '=', move.bora_cn_pm1_id.id),
                ('summary', 'ilike', 'Credit Note Approval'),
            ]).unlink()
            if move.bora_cn_pm2_id:
                move._create_cn_approval_activity(move.bora_cn_pm2_id, 'Confirm')

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """If user closes the wizard without selecting approvers, reset the credit note back to draft."""
        move = self.bora_cn_move_id
        if move and move.state == 'credit_note_approval_pending' and not move.bora_cn_pm1_id:
            pre_state = move.bora_cn_pre_approval_state or 'draft'
            move.write({
                'state': pre_state,
                'bora_cn_pre_approval_state': False,
            })
        return {'type': 'ir.actions.act_window_close'}
