# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsPurchaseReceiptApprovalReasonWizard(models.TransientModel):
    _name = 'ks.purchase.receipt.approval.reason.wizard'
    _description = 'KS Purchase Receipt Approval / Rejection Reason Wizard'

    ks_picking_id = fields.Many2one('stock.picking', string='Receipt', required=True)
    ks_action_type = fields.Selection([
        ('approve', 'Approve'),
        ('reject', 'Reject'),
    ], string='Action', required=True)
    ks_reason = fields.Text(
        string='Reason', required=True,
        placeholder='Please enter a reason (required)...')

    ks_is_rejection = fields.Boolean(compute='_compute_labels')
    ks_action_label = fields.Char(compute='_compute_labels')

    @api.depends('ks_action_type')
    def _compute_labels(self):
        for rec in self:
            rec.ks_is_rejection = rec.ks_action_type == 'reject'
            rec.ks_action_label = _('Rejection') if rec.ks_is_rejection else _('Approval')

    def action_submit(self):
        self.ensure_one()
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_('Reason is required. Please provide a reason before proceeding.'))
        reason = self.ks_reason.strip()
        if self.ks_action_type == 'approve':
            self.ks_picking_id._ks_do_approve_receipt_with_reason(reason, self.env.user)
        else:
            self.ks_picking_id.ks_do_reject_receipt(reason)
        return {'type': 'ir.actions.act_window_close'}
