# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ReKYCRequestWizard(models.TransientModel):
    _name = 'rekyc.request.wizard'
    _description = 'Re-KYC Request Form'

    partner_id = fields.Many2one('res.partner', string='Contact', domain="[('id', '=', active_id)]", tracking=True)
    remark = fields.Char('Remark', required=True)

    def action_rekyc_request(self):
        self.ensure_one()
        partner = self.partner_id.sudo()
        if not partner:
            return

        # Log remark in chatter
        partner.message_post(
            body=f"Re-KYC Requested: {self.remark}",
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        # Open KYC wizard pre-filled with existing data (works for both Indian and overseas partners)
        return {
            'name': _('Re-KYC Form'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.kyc.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': partner.id,
                'is_rekyc': True,
                'rekyc_remark': self.remark,
            },
        }
