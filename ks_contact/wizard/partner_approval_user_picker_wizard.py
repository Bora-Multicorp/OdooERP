# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PartnerApprovalUserPickerWizard(models.TransientModel):
    _name = 'partner.approval.user.picker.wizard'
    _description = 'Partner Approval Users Picker'

    partner_id = fields.Many2one('res.partner', string='Contact (Vendor)', required=True)

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
        """Create approval lines on partner and set approval_status to to_approve (same as KYC flow)."""
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(_("Contact is missing."))
        if not self.approver1_user or not self.approver2_user:
            raise ValidationError(_("Please select both Approver 1 and Approver 2."))

        from odoo import Command
        # Replace any previous approval lines (e.g. after reject) with new approvers
        self.partner_id.write({
            'approval_line_ids': [
                Command.clear(),
                Command.create({'sequence': 1, 'user_id': self.approver1_user.id}),
                Command.create({'sequence': 2, 'user_id': self.approver2_user.id}),
            ],
            'approval_status': 'to_approve',
            'is_rejected': False,
        })
        self.partner_id._schedule_sequential_approval_activities()
        return {'type': 'ir.actions.act_window_close'}
