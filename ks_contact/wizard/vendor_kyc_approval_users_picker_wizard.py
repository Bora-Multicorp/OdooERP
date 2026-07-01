# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class POConfirmationApprovalUsersPicker(models.TransientModel):
    _name = 'vendor.kyc.approval.user.picker.wizard'
    _description = 'vendor.kyc.approval users picker'

    kyc_id = fields.Many2one('res.partner.kyc.approval', string="Approval for Vendor Kyc Confirmation")
    ks_is_update_mode = fields.Boolean(string='Is Update Mode', default=False)
    ks_pm1_already_approved = fields.Boolean(string='PM1 Already Approved', default=False)
    ks_is_two_way = fields.Boolean(string='Is Two Way', compute='_compute_ks_is_two_way')
    ks_approval_info = fields.Html(compute='_compute_approval_info', readonly=True)

    approver1_user_ids = fields.Many2many(
        comodel_name='res.users',
        compute='_compute_approver_user_ids',
        string="Available Approver 1 Users",
        store=False
    )

    approver2_user_ids = fields.Many2many(
        comodel_name='res.users',
        compute='_compute_approver_user_ids',
        string="Available Approver 2 Users",
        store=False
    )

    approver1_user = fields.Many2one(
        comodel_name='res.users',
        string="Approver 1",
        required=True,
        domain="[('id', 'in', approver1_user_ids)]"
    )

    approver2_user = fields.Many2one(
        comodel_name='res.users',
        string="Approver 2",
        required=False,
        domain="[('id', 'in', approver2_user_ids)]"
    )

    add_button_disabled = fields.Boolean(
        string="Disable Add Button",
        compute='_compute_add_button_disabled'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        config = self.env['vendor.approval.config'].get_config()
        mode = config.ks_approval_mode if config else 'two_way'
        res['ks_is_two_way'] = (mode == 'two_way')

        is_update = self.env.context.get('ks_is_update', False)
        kyc_id = self.env.context.get('default_kyc_id') or res.get('kyc_id')
        if is_update and kyc_id:
            kyc = self.env['res.partner.kyc.approval'].browse(kyc_id)
            existing_pm1 = kyc.approval_users_ids.filtered(
                lambda l: l.sequence == 1 and l.state == 'approve'
            )[:1]
            if existing_pm1:
                res['ks_pm1_already_approved'] = True
                res['approver1_user'] = existing_pm1.user_id.id
        return res

    @api.depends('kyc_id')
    def _compute_ks_is_two_way(self):
        config = self.env['vendor.approval.config'].get_config()
        is_two_way = config.ks_approval_mode == 'two_way' if config else True
        for rec in self:
            rec.ks_is_two_way = is_two_way

    @api.depends('kyc_id', 'approver1_user', 'ks_is_update_mode', 'ks_is_two_way')
    def _compute_approval_info(self):
        for wiz in self:
            html = ''
            if wiz.ks_is_update_mode and wiz.kyc_id:
                approver1_line = wiz.kyc_id.approval_users_ids.filtered(
                    lambda l: l.sequence == 1 and l.state == 'approve'
                )[:1]
                if approver1_line:
                    html += (
                        '<div class="alert alert-success" role="alert">'
                        '<strong>&#10003; Approver 1 (%s) has already approved this request.</strong>'
                        ' Keeping the same Approver 1 will preserve their approval.'
                        '</div>'
                    ) % approver1_line.user_id.name
            if wiz.ks_is_two_way:
                html += (
                    '<div class="alert alert-info">'
                    '<p>KYC submission requires approval. Approval will be sequential (Approver 1 first, then Approver 2).</p>'
                    '</div>'
                )
            else:
                html += (
                    '<div class="alert alert-info">'
                    '<p>KYC submission requires Approver 1 only (Single Level Approval).</p>'
                    '</div>'
                )
            wiz.ks_approval_info = html

    @api.depends('kyc_id')
    def _compute_approver_user_ids(self):
        """Compute available approver users from config"""
        for rec in self:
            config = self.env['vendor.approval.config'].get_config()
            if config:
                rec.approver1_user_ids = config.ks_approver_1_ids
                rec.approver2_user_ids = config.ks_approver_2_ids
            else:
                rec.approver1_user_ids = False
                rec.approver2_user_ids = False

    @api.depends('approver1_user', 'approver2_user', 'ks_is_two_way')
    def _compute_add_button_disabled(self):
        for rec in self:
            if rec.ks_is_two_way:
                rec.add_button_disabled = not (rec.approver1_user and rec.approver2_user)
            else:
                rec.add_button_disabled = not rec.approver1_user

    @api.onchange('approver1_user')
    def _onchange_approver1_user(self):
        """Validate approver 1 selection"""
        if self.approver1_user and self.approver2_user == self.approver1_user:
            self.approver2_user = False

    @api.onchange('approver2_user')
    def _onchange_approver2_user(self):
        """Validate approver 2 selection"""
        if self.approver2_user and self.approver1_user == self.approver2_user:
            self.approver1_user = False

    def add_users_for_approval(self):
        """Add selected users to approval workflow (sequential).

        When opened via 'Update Approvals' (ks_is_update=True in context), the old
        activities and approval_users_ids are reset HERE — only after the user clicks OK.
        Clicking the wizard Cancel button leaves everything completely untouched.
        """
        if not self.kyc_id:
            raise ValidationError(_("KYC record is missing."))

        if not self.approver1_user:
            raise ValidationError(_("Please select Approver 1."))
        if self.ks_is_two_way and not self.approver2_user:
            raise ValidationError(_("Please select both Approver 1 and Approver 2."))

        is_update = self.env.context.get('ks_is_update', False)

        if is_update:
            existing_pm1 = self.kyc_id.approval_users_ids.filtered(
                lambda l: l.sequence == 1 and l.state == 'approve'
            )[:1]
            if existing_pm1 and existing_pm1.user_id != self.approver1_user:
                raise ValidationError(_(
                    "Approver 1 (%s) has already approved this request and cannot be changed."
                ) % existing_pm1.user_id.name)

        # Check if PM1 unchanged and already approved
        preserve_pm1 = False
        pm1_action_date = None
        if is_update and self.approver1_user:
            existing_pm1 = self.kyc_id.approval_users_ids.filtered(
                lambda l: l.sequence == 1 and l.state == 'approve'
            )[:1]
            if existing_pm1 and existing_pm1.user_id == self.approver1_user:
                preserve_pm1 = True
                pm1_action_date = existing_pm1.action_date

        if is_update:
            # Silently cancel old activities (scoped to KYC summary + current approver users)
            self.kyc_id._ks_cancel_pending_kyc_activities(mark_done=False)
            # Clear old approval lines and reset state to 'draft' so the write below
            # moves it cleanly back to 'pending' with fresh approvers
            self.kyc_id.write({
                'approval_users_ids': [(5, 0, 0)],
                'state': 'draft',
                'assigned_to': False,
            })
            msg = (
                _('Approval request updated by %s. Approver 1 (%s) approval preserved; only Approver 2 updated.')
                % (self.env.user.name, self.approver1_user.name)
                if preserve_pm1
                else _('Approval request updated by %s. Previous approvers cancelled.') % self.env.user.name
            )
            self.kyc_id.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')

        # Build new approval lines
        approval_vals = [
            (0, 0, {'sequence': 1, 'user_id': self.approver1_user.id}),
        ]
        if self.ks_is_two_way and self.approver2_user:
            approval_vals.append((0, 0, {'sequence': 2, 'user_id': self.approver2_user.id}))

        # Write approval users and trigger sequential approval flow
        self.kyc_id.write({
            'approval_users_ids': approval_vals,
            'state': 'pending',
            'kyc_approval_creator': self.env.user.id,
        })

        if preserve_pm1:
            # Restore PM1 approval on the new line
            new_pm1_line = self.kyc_id.approval_users_ids.filtered(
                lambda l: l.sequence == 1 and l.user_id == self.approver1_user
            )[:1]
            if new_pm1_line:
                new_pm1_line.write({'state': 'approve', 'action_date': pm1_action_date or fields.Datetime.now()})
            # Remove PM1 activity (already approved) and schedule PM2 directly
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'res.partner.kyc.approval'),
                ('res_id', '=', self.kyc_id.id),
                ('user_id', '=', self.approver1_user.id),
            ]).unlink()
            self.kyc_id._schedule_sequential_approval_activities()
        else:
            # Create activity only for first approver (sequential approval)
            self.kyc_id._schedule_sequential_approval_activities()
