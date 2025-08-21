

from odoo import models, api
from odoo.exceptions import UserError

class SendEmailToVendorOnPayment(models.TransientModel):
    _inherit = 'account.payment.register'


    def action_create_payments(self):
        super().action_create_payments()

        print('context =>', self._context)

        # print('payment ids =>', self.payment_id)

        # if not self.payment_ids:
        #     return

        # template = self.env.ref('bora_sale.vendor_payment_email_template', raise_if_not_found=False)

        # if not template:
        #     raise UserError("Email template 'vendor_payment_email_template' not found. Please check its XML ID.")
        
        # for payment in self.payment_ids:
        #     try:
        #         template.sudo().send_mail(payment.id, force_send=True)
        #     except Exception as e:
        #         print(f"Error sending email for payment ID {payment.id}: {e}")
                
        return {}




class abc(models.Model):
    _inherit = 'account.move'

    @api.depends("move_type")
    def _compute_is_vendor_payment(self):
        for rec in self:
            print('------------   rec =>', rec)

