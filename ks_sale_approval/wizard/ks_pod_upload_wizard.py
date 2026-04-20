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

        # Render body from template; fall back to a plain default
        template = self.env.ref(
            'ks_sale_approval.mail_template_pod_email', raise_if_not_found=False
        )
        if self.ks_message:
            body_html = self.ks_message
        elif template:
            body_html = template._render_field('body_html', picking.ids)[picking.id]
        else:
            body_html = _(
                '<p>Dear %(name)s,</p>'
                '<p>Please find attached the Proof of Delivery for your order '
                '<strong>%(order)s</strong>.</p>'
                '<p>Thank you for your business.</p>'
            ) % {'name': picking.partner_id.name, 'order': picking.name}

        subject = _('Proof of Delivery: %s') % picking.name

        # Send email directly via mail.mail
        self.env['mail.mail'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'email_from': picking.company_id.email_formatted or self.env.user.email_formatted,
            'recipient_ids': [(4, picking.partner_id.id)],
            'attachment_ids': [(4, attachment.id)],
            'auto_delete': False,
        }).send()

        # Log in chatter so there's an audit trail
        picking.message_post(
            body=_('POD email sent to %s with attachment <em>%s</em>.') % (
                picking.partner_id.email, self.ks_pod_filename or 'POD.pdf'),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Mark POD as sent
        picking.write({
            'ks_pod_sent': True,
            'ks_pod_attachment_id': attachment.id,
        })

        return {'type': 'ir.actions.act_window_close'}
