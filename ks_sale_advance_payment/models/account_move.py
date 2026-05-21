# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        """Allow advance sale order line updates triggered during invoice confirmation."""
        return super(AccountMove, self.with_context(allow_advance_line_write=True)).action_post()
