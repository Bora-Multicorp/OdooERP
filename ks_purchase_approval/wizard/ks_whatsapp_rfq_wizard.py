# -*- coding: utf-8 -*-
import base64
from urllib.parse import quote

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsRfqSendWizard(models.TransientModel):
    """Combined wizard for sending RFQ/PO via Email and WhatsApp"""
    _name = 'ks.rfq.send.wizard'
    _description = 'KS RFQ/PO Send Wizard (Email + WhatsApp)'

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        related='purchase_order_id.partner_id',
        readonly=True,
    )
    
    # Email fields
    email_to = fields.Char(
        string='Email To',
        compute='_compute_email_to',
        store=True,
        readonly=False,
    )
    email_subject = fields.Char(
        string='Subject',
        compute='_compute_email_content',
        store=True,
        readonly=False,
    )
    email_body = fields.Html(
        string='Email Body',
        compute='_compute_email_content',
        store=True,
        readonly=False,
    )
    template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
    )
    
    # WhatsApp fields
    mobile = fields.Char(
        string='WhatsApp Number',
        compute='_compute_mobile',
        store=True,
        readonly=False,
    )
    whatsapp_message = fields.Text(
        string='WhatsApp Message',
        compute='_compute_whatsapp_message',
        store=True,
        readonly=False,
    )
    has_mobile = fields.Boolean(
        string='Has Mobile',
        compute='_compute_mobile',
        store=True,
    )
    send_whatsapp = fields.Boolean(
        string='Also Send via WhatsApp',
        default=True,
    )
    
    # Document info
    is_rfq = fields.Boolean(
        string='Is RFQ',
        compute='_compute_is_rfq',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
        compute='_compute_attachments',
    )

    @api.depends('partner_id')
    def _compute_email_to(self):
        for record in self:
            record.email_to = record.partner_id.email or ''

    @api.depends('partner_id')
    def _compute_mobile(self):
        for record in self:
            mobile = record.partner_id.mobile or record.partner_id.phone or ''
            if mobile:
                mobile = ''.join(filter(lambda x: x.isdigit() or x == '+', mobile))
            record.mobile = mobile
            record.has_mobile = bool(mobile)

    @api.depends('purchase_order_id')
    def _compute_is_rfq(self):
        for record in self:
            record.is_rfq = record.purchase_order_id.state in ['draft', 'sent']

    @api.depends('purchase_order_id', 'template_id')
    def _compute_email_content(self):
        for record in self:
            if not record.purchase_order_id or not record.template_id:
                record.email_subject = ''
                record.email_body = ''
                continue
            
            # Render template
            template = record.template_id
            po = record.purchase_order_id
            
            # Get rendered values
            rendered = template._render_field('subject', [po.id], compute_lang=True)
            record.email_subject = rendered.get(po.id, '')
            
            rendered_body = template._render_field('body_html', [po.id], compute_lang=True)
            record.email_body = rendered_body.get(po.id, '')

    @api.depends('purchase_order_id')
    def _compute_attachments(self):
        for record in self:
            if not record.purchase_order_id:
                record.attachment_ids = False
                continue
            
            po = record.purchase_order_id
            # Generate PDF report
            if po.state in ['draft', 'sent']:
                report = self.env.ref('purchase.report_purchase_quotation')
            else:
                report = self.env.ref('purchase.action_report_purchase_order')
            
            pdf_content, _ = report._render_qweb_pdf(report.id, [po.id])
            
            # Create attachment
            attachment = self.env['ir.attachment'].create({
                'name': f"{po.name}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'purchase.order',
                'res_id': po.id,
                'mimetype': 'application/pdf',
            })
            record.attachment_ids = [(6, 0, [attachment.id])]

    @api.depends('purchase_order_id', 'is_rfq')
    def _compute_whatsapp_message(self):
        for record in self:
            po = record.purchase_order_id
            if not po:
                record.whatsapp_message = ''
                continue
            
            doc_type = _('Request for Quotation') if record.is_rfq else _('Purchase Order')
            
            # Build order lines summary
            lines_text = []
            for line in po.order_line.filtered(lambda l: not l.display_type)[:10]:
                lines_text.append(
                    f"• {line.product_id.name}: {line.product_qty} {line.product_uom.name} @ {po.currency_id.symbol}{line.price_unit:.2f}"
                )
            lines_summary = '\n'.join(lines_text)
            if len(po.order_line.filtered(lambda l: not l.display_type)) > 10:
                lines_summary += _("\n... and %d more items") % (len(po.order_line) - 10)
            
            # Get portal URL
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            portal_url = f"{base_url}/my/purchase/{po.id}"
            
            message = _("""Dear %(vendor)s,

Please find the details of %(doc_type)s: *%(po_name)s*

*Order Details:*
%(lines)s

*Total Amount:* %(currency)s %(total)s

*Expected Delivery:* %(date)s

📄 *View/Download Document:* %(url)s

Best regards,
%(company)s
%(user)s""") % {
                'vendor': po.partner_id.name,
                'doc_type': doc_type,
                'po_name': po.name,
                'lines': lines_summary,
                'currency': po.currency_id.symbol,
                'total': f"{po.amount_total:,.2f}",
                'date': po.date_planned.strftime('%Y-%m-%d') if po.date_planned else 'TBD',
                'url': portal_url,
                'company': po.company_id.name,
                'user': self.env.user.name,
            }
            record.whatsapp_message = message

    def action_send_email_and_whatsapp(self):
        """Send email and open WhatsApp"""
        self.ensure_one()
        
        po = self.purchase_order_id
        
        # Send email
        if self.email_to:
            mail_values = {
                'subject': self.email_subject,
                'body_html': self.email_body,
                'email_to': self.email_to,
                'model': 'purchase.order',
                'res_id': po.id,
                'attachment_ids': [(6, 0, self.attachment_ids.ids)] if self.attachment_ids else False,
            }
            mail = self.env['mail.mail'].create(mail_values)
            mail.send()
            
            # Post message in chatter
            po.message_post(
                body=self.email_body,
                subject=self.email_subject,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
                attachment_ids=self.attachment_ids.ids,
            )
            
            # Mark RFQ as sent
            if po.state == 'draft':
                po.write({'state': 'sent'})
        
        # Open WhatsApp if enabled and mobile exists
        if self.send_whatsapp and self.has_mobile and self.mobile:
            # Log WhatsApp send in chatter
            po.message_post(
                body=_("WhatsApp message sent to %s (%s)") % (self.partner_id.name, self.mobile),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            
            # URL encode the message
            encoded_message = quote(self.whatsapp_message)
            whatsapp_url = f"https://api.whatsapp.com/send?phone={self.mobile}&text={encoded_message}"
            
            return {
                'type': 'ir.actions.act_url',
                'url': whatsapp_url,
                'target': 'new',
            }
        
        return {'type': 'ir.actions.act_window_close'}

    def action_send_email_only(self):
        """Send email only"""
        self.send_whatsapp = False
        return self.action_send_email_and_whatsapp()

    def action_send_whatsapp_only(self):
        """Open WhatsApp only (without sending email)"""
        self.ensure_one()
        
        if not self.mobile:
            raise UserError(_("No mobile number found for vendor %s.") % self.partner_id.name)
        
        # Log in chatter
        self.purchase_order_id.message_post(
            body=_("WhatsApp message sent to %s (%s)") % (self.partner_id.name, self.mobile),
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )
        
        # URL encode the message
        encoded_message = quote(self.whatsapp_message)
        whatsapp_url = f"https://api.whatsapp.com/send?phone={self.mobile}&text={encoded_message}"
        
        return {
            'type': 'ir.actions.act_url',
            'url': whatsapp_url,
            'target': 'new',
        }
