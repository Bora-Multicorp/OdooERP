# -*- coding: utf-8 -*-

from odoo import fields, models


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

        # Reset KYC and approval flags
        update_vals = {
            'is_kyc': False,
            'is_approved': False,
            'deadline': False,
        }

        # Adjust partner ranks
        if partner.is_vendor:
            update_vals['supplier_rank'] = 0


        partner.write(update_vals)

        # Log remark in chatter
        partner.message_post(
            body=f"Re-KYC Requested: {self.remark}",
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return {'type': 'ir.actions.act_window_close'}
