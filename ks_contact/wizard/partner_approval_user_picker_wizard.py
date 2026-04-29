# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PartnerApprovalUserPickerWizard(models.TransientModel):
    _name = 'partner.approval.user.picker.wizard'
    _description = 'Partner Approval Users Picker'

    partner_id = fields.Many2one('res.partner', string='Contact (Vendor)', required=True)
    ks_is_update_mode = fields.Boolean(string='Is Update Mode', default=False)
    ks_approval_info = fields.Html(compute='_compute_approval_info', readonly=True)

    approver1_user_ids = fields.Many2many(
        comodel_name='res.users',
        compute='_compute_approver_user_ids',
        string='Available Approver 1 Users',
        store=False,
    )
    approver2_user_ids = fields.Many2many(
        comodel_name='res.users',
        compute='_compute_approver_user_ids',
        string='Available Approver 2 Users',
        store=False,
    )
    approver1_user = fields.Many2one(
        'res.users',
        string='Approver 1',
        required=True,
        domain="[('id', 'in', approver1_user_ids)]",
    )
    approver2_user = fields.Many2one(
        'res.users',
        string='Approver 2',
        required=True,
        domain="[('id', 'in', approver2_user_ids)]",
    )
    add_button_disabled = fields.Boolean(compute='_compute_add_button_disabled')

    @api.depends('partner_id', 'approver1_user', 'ks_is_update_mode')
    def _compute_approval_info(self):
        for wiz in self:
            html = ''
            if wiz.ks_is_update_mode and wiz.partner_id:
                approver1_line = wiz.partner_id.approval_line_ids.filtered(
                    lambda l: l.sequence == 1 and l.state == 'approve'
                )[:1]
                if approver1_line:
                    html += (
                        '<div class="alert alert-success" role="alert">'
                        '<strong>&#10003; Approver 1 (%s) has already approved this request.</strong>'
                        ' Keeping the same Approver 1 will preserve their approval.'
                        '</div>'
                    ) % approver1_line.user_id.name
            html += (
                '<div class="alert alert-info">'
                '<p>Vendor approval requires Approver 1 and Approver 2. Approval will be sequential (Approver 1 first, then Approver 2).</p>'
                '</div>'
            )
            wiz.ks_approval_info = html

    @api.depends('partner_id')
    def _compute_approver_user_ids(self):
        config = self.env['vendor.approval.config'].get_config()
        for rec in self:
            if config:
                rec.approver1_user_ids = config.ks_approver_1_ids
                rec.approver2_user_ids = config.ks_approver_2_ids
            else:
                rec.approver1_user_ids = False
                rec.approver2_user_ids = False

    @api.depends('approver1_user', 'approver2_user')
    def _compute_add_button_disabled(self):
        for rec in self:
            rec.add_button_disabled = not (rec.approver1_user and rec.approver2_user)

    @api.onchange('approver1_user')
    def _onchange_approver1_user(self):
        if self.approver1_user and self.approver2_user == self.approver1_user:
            self.approver2_user = False

    @api.onchange('approver2_user')
    def _onchange_approver2_user(self):
        if self.approver2_user and self.approver1_user == self.approver2_user:
            self.approver1_user = False

    def add_users_for_approval(self):
        """Create approval lines on partner and set approval_status to to_approve.

        When opened via 'Update Approvals' (ks_is_update=True in context), the old
        activities are silently cancelled HERE — only after the user clicks OK.
        Clicking the wizard Cancel button leaves everything completely untouched.
        """
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(_("Contact is missing."))
        if not self.approver1_user or not self.approver2_user:
            raise ValidationError(_("Please select both Approver 1 and Approver 2."))

        is_update = self.env.context.get('ks_is_update', False)

        # Check if PM1 unchanged and already approved
        preserve_pm1 = False
        pm1_action_date = None
        if is_update and self.approver1_user:
            existing_pm1 = self.partner_id.approval_line_ids.filtered(
                lambda l: l.sequence == 1 and l.state == 'approve'
            )[:1]
            if existing_pm1 and existing_pm1.user_id == self.approver1_user:
                preserve_pm1 = True
                pm1_action_date = existing_pm1.action_date

        if is_update:
            # Silently cancel old activities (scoped: summary 'Vendor Approval' + approver users)
            self.partner_id._ks_cancel_pending_partner_approval_activities(mark_done=False)
            msg = (
                _('Approval request updated by %s. Approver 1 (%s) approval preserved; only Approver 2 updated.')
                % (self.env.user.name, self.approver1_user.name)
                if preserve_pm1
                else _('Approval request updated by %s. Previous approvers cancelled.') % self.env.user.name
            )
            self.partner_id.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')

        from odoo import Command
        # Replace approval lines with new approvers (Command.clear() handles old lines)
        self.partner_id.write({
            'approval_line_ids': [
                Command.clear(),
                Command.create({'sequence': 1, 'user_id': self.approver1_user.id}),
                Command.create({'sequence': 2, 'user_id': self.approver2_user.id}),
            ],
            'approval_status': 'to_approve',
            'is_rejected': False,
        })

        if preserve_pm1:
            # Restore PM1 approval on the new line
            new_pm1_line = self.partner_id.approval_line_ids.filtered(
                lambda l: l.sequence == 1 and l.user_id == self.approver1_user
            )[:1]
            if new_pm1_line:
                new_pm1_line.sudo().write({'state': 'approve', 'action_date': pm1_action_date or fields.Datetime.now()})
            # Remove PM1 activity (already approved)
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', self.partner_id.id),
                ('user_id', '=', self.approver1_user.id),
            ]).unlink()
            # Schedule PM2 activity directly
            self.partner_id._schedule_sequential_approval_activities()
        else:
            self.partner_id._schedule_sequential_approval_activities()
        return {'type': 'ir.actions.act_window_close'}
