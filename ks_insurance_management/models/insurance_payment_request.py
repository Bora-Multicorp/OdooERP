# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class InsurancePaymentApprover(models.Model):
    """Single-approver master for all insurance payment and top-up requests.
    Only one active approver is allowed per company at any time.
    """
    _name = 'insurance.payment.approver'
    _description = 'Insurance Payment Approver'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        help='This user receives approval activities for all insurance payments and top-ups.',
    )
    email = fields.Char(related='user_id.email', string='Email', readonly=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

    @api.constrains('active', 'company_id', 'user_id')
    def _check_single_active_approver(self):
        """Only ONE active approver is allowed per company."""
        for rec in self:
            if not rec.active:
                continue
            duplicate = self.search([
                ('company_id', '=', rec.company_id.id),
                ('active', '=', True),
                ('id', '!=', rec.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f"Only one active Insurance Payment Approver is allowed per company. "
                    f"'{duplicate.name}' is already the active approver for "
                    f"'{rec.company_id.name}'. Please deactivate them first."
                )
