# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class KsGrnApproveWizard(models.TransientModel):
    _name = 'ks.grn.approve.wizard'
    _description = 'Approve GRN (Receipt)'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Receipt',
        required=True,
        ondelete='cascade',
    )
    ks_reason = fields.Text(
        string='Reason for approval',
        required=True,
        help='Please provide a reason for the approval (required).',
    )

    def action_submit_approval(self):
        self.ensure_one()
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_('Reason for approval is required.'))
        self.picking_id._ks_grn_do_approve(self.ks_reason.strip())
        return {'type': 'ir.actions.act_window_close'}
