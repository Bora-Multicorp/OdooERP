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
    insurance_type_id = fields.Many2one(
        related='policy_id.insurance_type_id', string='Insurance Type', readonly=True)
    company_id = fields.Many2one(
        related='policy_id.company_id', string='Company Name', readonly=True)
    insurance_company_id = fields.Many2one(
        related='policy_id.insurance_company_id', string='Insurance Company', readonly=True)
    cover_amount_words = fields.Char(
        related='policy_id.sum_insured_words', string='Cover Amount (in words)', readonly=True)
    premium = fields.Float(
        string='Premium (Incl. GST)',
        help='Updated premium inclusive of GST. Will be saved to the policy after payment is posted.')
    agent_id = fields.Many2one(
        related='policy_id.agent_id', string='Agent', readonly=True)
    expiry_date = fields.Date(
        related='policy_id.expiry_date', string='Expiry Date', readonly=True)
    approver_id = fields.Many2one(
        'insurance.payment.approver',
        string='Payment Approver',
        required=True,
        domain="[('company_id', '=', company_id)]",
        help='Select the approver who will approve this top-up payment.',
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

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        policy_id = self.env.context.get('default_policy_id') or res.get('policy_id')
        if policy_id:
            policy = self.env['insurance.policy'].browse(policy_id)
            if policy.exists():
                if 'premium' in fields_list and 'premium' not in res:
                    res['premium'] = policy.premium
                self._sync_approvers_for_policy(policy)
        res.pop('approver_id', None)
        return res

    def _sync_approvers_for_policy(self, policy):
        """Ensure active Approval Authorities users are synced as insurance.payment.approver records."""
        comp = policy.company_id or self.env.company
        if 'bora.insurance.approval.config' in self.env:
            config = self.env['bora.insurance.approval.config'].get_config(comp)
            if config:
                config._sync_payment_approvers()

    @api.onchange('policy_id')
    def _onchange_policy_id(self):
        if self.policy_id:
            self.premium = self.policy_id.premium
            self._sync_approvers_for_policy(self.policy_id)

    def action_confirm(self):
        """Submit top-up for approval. Sum insured and premium are updated only after payment is posted."""
        self.ensure_one()
        if self.topup_amount <= 0:
            raise UserError("Top-up amount must be greater than zero.")
        if not self.approver_id:
            raise UserError("Please select a Payment Approver.")

        policy = self.policy_id
        approver = self.approver_id

        # Store pending topup and premium; actual update happens in account_payment.action_post
        policy.write({
            'pending_topup_amount': self.topup_amount,
            'pending_topup_premium': self.premium,
            'pending_topup_approver_id': approver.id,
            'payment_status': 'requested',
        })

        new_sum_insured = policy.initial_sum_insured + self.topup_amount
        policy._notify_approver(
            approver,
            summary=f'Top-up Approval Required — {policy.policy_number}',
            note=(
                f'A top-up of <b>₹{self.topup_amount:,.2f}</b> has been requested for '
                f'policy <b>{policy.policy_number}</b>.<br/>'
                f'New Sum Insured (after payment): <b>₹{new_sum_insured:,.2f}</b><br/>'
                f'Updated Premium (Incl. GST): <b>₹{self.premium:,.2f}</b><br/>'
                f'Requested by: <b>{self.env.user.name}</b><br/>'
                f'Please approve the corresponding payment.'
            ),
        )

        policy.message_post(
            body=(
                f'Top-up of <b>₹{self.topup_amount:,.2f}</b> requested by '
                f'<b>{self.env.user.name}</b>. '
                f'Pending approval from <b>{approver.name}</b>.'
            ),
        )
        return {'type': 'ir.actions.act_window_close'}
