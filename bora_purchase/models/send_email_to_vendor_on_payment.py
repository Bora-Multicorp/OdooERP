

from odoo import models, api, fields
from .utility import to_unicode_bold

class SendEmailToVendorOnPayment(models.Model):
    _inherit = 'account.move'

    is_vendor_bill = fields.Char()

    def _invoice_paid_hook(self):
        super(SendEmailToVendorOnPayment, self)._invoice_paid_hook()

        if self.type_name == 'Invoice':
            return  # Only proceed for vendor bills

        for record in self:
            payment = self.env['account.payment'].search([
                ('memo', '=', record.name)
            ], limit=1)

            if payment:
                template_id = self.env.ref('bora_purchase.email_template_vendor_payment_confirmation').id
                self.env['mail.template'].sudo().browse(template_id).send_mail(
                    payment.id, 
                    force_send=True
                )

                record.message_post(body=f"Payment confirmation email sent to vendor for invoice {record.name}.")

                message = 'A payment confirmation email for bill %s has been sent to %s.' % (to_unicode_bold(self.name), to_unicode_bold(self.partner_id.name))
                self.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': 'Vendor Payment Email Sent',
                        'message': message,
                        'sticky': True,
                    }
                )

