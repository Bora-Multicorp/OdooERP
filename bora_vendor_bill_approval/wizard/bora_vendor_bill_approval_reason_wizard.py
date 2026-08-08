# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BoraVendorBillApprovalReasonWizard(models.TransientModel):
    _name = 'bora.vendor.bill.approval.reason.wizard'
    _description = 'Bora Vendor Bill Approval / Rejection Reason Wizard'

    bora_move_id = fields.Many2one('account.move', string='Vendor Bill', required=True)
    bora_action_type = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ], string='Action', required=True)
    bora_reason = fields.Text(
        string='Reason', required=True,
        placeholder='Please enter a reason (required)...')

    bora_is_rejection = fields.Boolean(compute='_compute_labels')
    bora_action_label = fields.Char(compute='_compute_labels')

    @api.depends('bora_action_type')
    def _compute_labels(self):
        for rec in self:
            rec.bora_is_rejection = rec.bora_action_type == 'reject'
            rec.bora_action_label = _('Rejection') if rec.bora_is_rejection else _('Approval')

    def action_submit(self):
        self.ensure_one()
        if not self.bora_reason or not self.bora_reason.strip():
            raise UserError(_('Reason is required. Please provide a reason before proceeding.'))
        reason = self.bora_reason.strip()
        if self.bora_action_type == 'approve':
            self.bora_move_id._bora_do_approve_bill_with_reason(reason, self.env.user)
        else:
            self.bora_move_id.bora_do_reject_bill(reason)
        return {'type': 'ir.actions.act_window_close'}
