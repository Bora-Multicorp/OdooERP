# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.exceptions import UserError


class InsurancePaymentRequestWizard(models.TransientModel):
    """Popup shown when clicking 'Request Payment' on a policy (single or multi).
    Lets the user confirm the approver before submitting.
    """
    _name = 'insurance.payment.request.wizard'
    _description = 'Insurance Payment Request Wizard'

    policy_ids = fields.Many2many(
        'insurance.policy',
        string='Policies',
        readonly=True,
    )
    approver_id = fields.Many2one(
        'insurance.payment.approver',
        string='Approver',
        required=True,
        help='The approver who will receive an approval activity.',
    )

    def action_confirm(self):
        """Submit payment request for each policy."""
        self.ensure_one()
        if not self.policy_ids:
            raise UserError("No policies selected.")

        approver = self.approver_id
        for policy in self.policy_ids:
            if policy.payment_status in ('requested', 'approved'):
                raise UserError(
                    f"Policy '{policy.policy_number}' already has a pending payment request."
                )
            if policy.payment_status == 'paid' and not policy.pending_topup_amount:
                raise UserError(
                    f"Policy '{policy.policy_number}' is already paid. "
                    f"Use 'Top Up Addon' to increase coverage."
                )

            policy.write({'payment_status': 'requested'})
            policy._notify_approver(
                approver,
                summary=f'Insurance Payment Approval — {policy.policy_number}',
                note=(
                    f'Payment request submitted for policy <b>{policy.policy_number}</b> '
                    f'({policy.insurance_type_id.name}).<br/>'
                    f'Premium Amount: <b>₹{policy.premium:,.2f}</b><br/>'
                    f'Requested by: <b>{self.env.user.name}</b><br/>'
                    f'Please approve or reject this request.'
                ),
            )
            policy.message_post(
                body=(
                    f'Payment requested by <b>{self.env.user.name}</b>. '
                    f'Awaiting approval from <b>{approver.name}</b>.'
                ),
            )
        return {'type': 'ir.actions.act_window_close'}
