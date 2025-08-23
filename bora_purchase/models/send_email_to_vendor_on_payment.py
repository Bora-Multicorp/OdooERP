

from odoo import models, api, fields
import pprint

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

                message = 'A payment confirmation email for bill %s has been sent to %s.' % (self.to_unicode_bold(self.name), self.to_unicode_bold(self.partner_id.name))
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

    def to_unicode_bold(self, text):
        if not isinstance(text, str):
            text = str(text)

        char_map = {
            'A': '𝗔', 'B': '𝗕', 'C': '𝗖', 'D': '𝗗', 'E': '𝗘', 'F': '𝗙', 'G': '𝗚', 'H': '𝗛', 'I': '𝗜', 'J': '𝗝', 'K': '𝗞', 'L': '𝗟', 'M': '𝗠', 'N': '𝗡', 'O': '𝗢', 'P': '𝗣', 'Q': '𝗤', 'R': '𝗥', 'S': '𝗦', 'T': '𝗧', 'U': '𝗨', 'V': '𝗩', 'W': '𝗪', 'X': '𝗫', 'Y': '𝗬', 'Z': '𝗭',
            'a': '𝗮', 'b': '𝗯', 'c': '𝗰', 'd': '𝗱', 'e': '𝗲', 'f': '𝗳', 'g': '𝗴', 'h': '𝗵', 'i': '𝗶', 'j': '𝗷', 'k': '𝗸', 'l': '𝗹', 'm': '𝗺', 'n': '𝗻', 'o': '𝗼', 'p': '𝗽', 'q': '𝗾', 'r': '𝗿', 's': '𝘀', 't': '𝘁', 'u': '𝘂', 'v': '𝘃', 'w': '𝘄', 'x': '𝘅', 'y': '𝘆', 'z': '𝘇',
            '0': '𝟬', '1': '𝟭', '2': '𝟮', '3': '𝟯', '4': '𝟰', '5': '𝟱', '6': '𝟲', '7': '𝟳', '8': '𝟴', '9': '𝟵',
            '/': '/'
        }
        return ''.join(char_map.get(char, char) for char in text)


