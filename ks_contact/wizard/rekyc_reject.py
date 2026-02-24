# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import ValidationError


class ReKYCRejectWizard(models.TransientModel):
    _name = 'rekyc.reject.wizard'
    _description = 'Reject Re-KYC Request'

    kyc_id = fields.Many2one('res.partner.kyc.approval', required=True)
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.kyc_id:
            raise ValidationError(_('KYC record is required.'))
        self.kyc_id.action_reject_rekyc(self.reason)
        return {'type': 'ir.actions.act_window_close'}
