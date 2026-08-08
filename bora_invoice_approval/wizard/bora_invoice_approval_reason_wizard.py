# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BoraInvoiceApprovalReasonWizard(models.TransientModel):
    _name = 'bora.invoice.approval.reason.wizard'
    _description = 'Bora Invoice Approval / Rejection Reason Wizard'

    bora_inv_move_id = fields.Many2one('account.move', string='Invoice', required=True)
    bora_inv_action_type = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ], string='Action', required=True)
    bora_inv_reason = fields.Text(
        string='Reason', required=True,
        placeholder='Please enter a reason (required)...')

    bora_inv_is_rejection = fields.Boolean(compute='_compute_labels')
    bora_inv_action_label = fields.Char(compute='_compute_labels')

    @api.depends('bora_inv_action_type')
    def _compute_labels(self):
        for rec in self:
            rec.bora_inv_is_rejection = rec.bora_inv_action_type == 'reject'
            rec.bora_inv_action_label = _('Rejection') if rec.bora_inv_is_rejection else _('Approval')

    def action_submit(self):
        self.ensure_one()
        if not self.bora_inv_reason or not self.bora_inv_reason.strip():
            raise UserError(_('Reason is required. Please provide a reason before proceeding.'))
        reason = self.bora_inv_reason.strip()
        if self.bora_inv_action_type == 'approve':
            self.bora_inv_move_id._bora_do_approve_inv_with_reason(reason, self.env.user)
        else:
            self.bora_inv_move_id.bora_inv_do_reject(reason)
        return {'type': 'ir.actions.act_window_close'}
