# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_mail_template(self):
        """Use our custom 'Invoice Sent to Customer' template for out_invoice.
        Base account template is in noupdate="1" so we use our own template."""
        self.ensure_one()
        if self.move_type == 'out_refund':
            return self.env.ref('account.email_template_edi_credit_note')
        # Out invoice: use our custom template
        template = self.env.ref(
            'ks_automail.email_template_invoice_sent_to_customer',
            raise_if_not_found=False,
        )
        if template:
            return template
        return self.env.ref('account.email_template_edi_invoice')
