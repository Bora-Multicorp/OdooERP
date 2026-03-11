# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class KsGrnRejectWizard(models.TransientModel):
    _name = 'ks.grn.reject.wizard'
    _description = 'Reject GRN (Receipt)'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Receipt',
        required=True,
        ondelete='cascade',
    )
    ks_reason = fields.Text(
        string='Reason for rejection',
        required=True,
        help='Please provide a reason for the rejection (required).',
    )

    def action_submit_rejection(self):
        self.ensure_one()
        if not self.ks_reason or not self.ks_reason.strip():
            raise UserError(_('Reason for rejection is required.'))
        self.picking_id._ks_grn_do_reject(self.ks_reason.strip())
        return {'type': 'ir.actions.act_window_close'}
