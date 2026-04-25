# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class InsurancePolicyPaymentWizard(models.TransientModel):
    """Top-up wizard opened by the 'Top Up Addon' button on the policy form.
    Increases the sum insured immediately and triggers the approval workflow.
    """
    _name = 'insurance.policy.payment.wizard'
    _description = 'Insurance Policy Top-up Wizard'

    policy_id = fields.Many2one(
        'insurance.policy',
        string='Policy',
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(related='policy_id.currency_id', readonly=True)
    current_sum_insured = fields.Float(
        string='Current Sum Insured',
        related='policy_id.initial_sum_insured',
        readonly=True,
    )
    topup_amount = fields.Float(
        string='Top-up Amount',
        required=True,
        help='Amount to add to the current sum insured.',
    )
    new_sum_insured = fields.Float(
        string='New Sum Insured',
        compute='_compute_new_sum_insured',
        help='Preview of the sum insured after this top-up is applied.',
    )

    @api.depends('current_sum_insured', 'topup_amount')
    def _compute_new_sum_insured(self):
        for rec in self:
            rec.new_sum_insured = (rec.current_sum_insured or 0.0) + (rec.topup_amount or 0.0)

    def action_confirm(self):
        """Apply the top-up and trigger the approval workflow."""
        self.ensure_one()
        if self.topup_amount <= 0:
            raise UserError("Top-up amount must be greater than zero.")

        policy = self.policy_id
        approver = policy._get_approver()
        if not approver:
            raise UserError(
                "No payment approver is configured. "
                "Please set one in Configuration → Payment Approvers."
            )

        # 1. Increase insured amount immediately (per spec)
        # 2. Set topup_flag and store pending amount for payment creation on approval
        policy.write({
            'initial_sum_insured': policy.initial_sum_insured + self.topup_amount,
            'topup_flag': True,
            'pending_topup_amount': self.topup_amount,
            'payment_status': 'requested',
        })

        # 3. Notify approver via activity on the policy
        policy._notify_approver(
            approver,
            summary=f'Top-up Approval Required — {policy.policy_number}',
            note=(
                f'A top-up of <b>₹{self.topup_amount:,.2f}</b> has been applied to '
                f'policy <b>{policy.policy_number}</b>.<br/>'
                f'New Sum Insured: <b>₹{policy.initial_sum_insured:,.2f}</b><br/>'
                f'Requested by: <b>{self.env.user.name}</b><br/>'
                f'Please approve the corresponding payment.'
            ),
        )

        policy.message_post(
            body=(
                f'Top-up of <b>₹{self.topup_amount:,.2f}</b> applied by '
                f'<b>{self.env.user.name}</b>. '
                f'New Sum Insured: <b>₹{policy.initial_sum_insured:,.2f}</b>. '
                f'Awaiting approval from <b>{approver.name}</b>.'
            ),
        )
        return {'type': 'ir.actions.act_window_close'}
