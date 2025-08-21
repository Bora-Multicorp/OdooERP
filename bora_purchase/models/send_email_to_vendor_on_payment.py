

from odoo import models, api, fields

class SendEmailToVendorOnPayment(models.Model):
    _inherit = 'account.move'

    is_vendor_bill = fields.Char()

    def _invoice_paid_hook(self):
        super(SendEmailToVendorOnPayment, self)._invoice_paid_hook()

        for record in self:
            payment = self.env['account.payment'].search([
                ('reconciled_invoice_ids', 'in', record.id),
                ('payment_type', '=', 'outbound'), # Filter for payments made to vendors
            ], limit=1)

            if payment:
                try:
                    # Get the ID of the email template using its external ID.
                    template_id = self.env.ref('bora_purchase.email_template_vendor_payment_confirmation').id
                    
                    # Use the `send_mail` method of the `mail.template` model.
                    # The `res_id` argument is the ID of the record you want
                    # to use for the template's context (the `object`).
                    # We pass the ID of the `payment` record we just found.
                    self.env['mail.template'].sudo().browse(template_id).send_mail(
                        payment.id, 
                        force_send=True
                    )

                    # Optional: Log a message to the chatter for confirmation.
                    record.message_post(body=f"Payment confirmation email sent to vendor for invoice {record.name}.")

                except Exception as e:
                    # Log any errors that occur during email sending.
                    # This is a good practice to prevent the hook from failing silently.
                    _logger.error("Failed to send vendor payment email for invoice %s. Error: %s", record.name, e)