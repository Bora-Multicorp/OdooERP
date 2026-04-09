# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64


class KsPodUploadWizard(models.TransientModel):
    _name = 'ks.pod.upload.wizard'
    _description = 'Upload Proof of Delivery (POD)'

    ks_picking_id = fields.Many2one('stock.picking', string='Delivery Order', required=True)
    ks_partner_id = fields.Many2one(related='ks_picking_id.partner_id', string='Customer', readonly=True)

    ks_pod_file = fields.Binary(string='POD File (PDF/DOC)', required=True, attachment=True)
    ks_pod_filename = fields.Char(string='Filename')
    ks_message = fields.Html(string='Message to Customer')

    def action_send_email(self):
        self.ensure_one()
        picking = self.ks_picking_id

        if not self.ks_pod_file:
            raise UserError(_('Please upload a POD file before sending the email.'))
        if not picking.partner_id or not picking.partner_id.email:
            raise UserError(_('The customer does not have an email address configured.'))

        # Create ir.attachment for the POD file
        attachment = self.env['ir.attachment'].create({
            'name': self.ks_pod_filename or 'POD.pdf',
            'datas': self.ks_pod_file,
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'type': 'binary',
        })

        # Compose and send email
        message_body = self.ks_message or _(
            '<p>Dear %s,</p>'
            '<p>Please find attached the Proof of Delivery for your order <strong>%s</strong>.</p>'
            '<p>Thank you for your business.</p>'
        ) % (picking.partner_id.name, picking.name)

        picking.message_post(
            body=message_body,
            subject=_('Proof of Delivery: %s') % picking.name,
            message_type='email',
            subtype_xmlid='mail.mt_comment',
            partner_ids=[picking.partner_id.id],
            attachment_ids=[attachment.id],
        )

        # Mark POD as sent on the picking
        picking.write({
            'ks_pod_sent': True,
            'ks_pod_attachment_id': attachment.id,
        })

        return {'type': 'ir.actions.act_window_close'}
