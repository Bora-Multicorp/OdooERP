# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


# ── Top-up Request ────────────────────────────────────────────────────────────────────────

class InsuranceTopup(models.Model):
    _name = 'insurance.topup'
    _description = 'Insurance Policy Top-up'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        default='New',
        readonly=True,
        copy=False,
    )
    policy_id = fields.Many2one(
        'insurance.policy',
        string='Policy',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    company_id = fields.Many2one(
        related='policy_id.company_id',
        store=True,
    )
    currency_id = fields.Many2one(
        related='policy_id.currency_id',
        store=True,
    )
    current_sum_insured = fields.Float(
        string='Current Sum Insured',
        related='policy_id.initial_sum_insured',
        readonly=True,
    )
    amount = fields.Float(
        string='Top-up Amount',
        required=True,
        tracking=True,
        help='The additional coverage amount to be added to the policy Sum Insured upon approval.',
    )
    new_sum_insured = fields.Float(
        string='New Sum Insured (After Top-up)',
        compute='_compute_new_sum_insured',
        store=True,
        help='Preview of the Sum Insured after this top-up is approved.',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    approver_id = fields.Many2one(
        'insurance.payment.approver',
        string='Approver',
        required=True,
        help='Single approver who must approve this top-up. '
             'Selected from the Insurance Payment Approvers master.',
        tracking=True,
    )

    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        domain=[('type', 'in', ['bank', 'cash'])],
        help='Bank or cash journal used to record the top-up premium payment.',
    )
    payment_date = fields.Date(
        string='Payment Date',
        default=fields.Date.today,
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        readonly=True,
        copy=False,
        help='Draft account payment created automatically when the top-up is approved.',
    )

    is_latest = fields.Boolean(
        string='Latest Top-up',
        default=False,
        copy=False,
        help='Flags the most recently approved top-up on this policy.',
    )
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
    )
    approved_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
        copy=False,
    )
    notes = fields.Text(string='Notes')

    # ── Computed ─────────────────────────────────────────────────────────────────────────

    @api.depends('policy_id.initial_sum_insured', 'amount')
    def _compute_new_sum_insured(self):
        for rec in self:
            rec.new_sum_insured = (rec.policy_id.initial_sum_insured or 0.0) + (rec.amount or 0.0)

    # ── ORM ──────────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('insurance.topup') or 'New'
                )
        return super().create(vals_list)

    # ── State actions ─────────────────────────────────────────────────────────────────────

    def action_submit(self):
        """Submit top-up for approval: assign an activity to the single approver."""
        self.ensure_one()
        if self.amount <= 0:
            raise UserError("Top-up amount must be greater than zero.")

        self.write({'state': 'pending'})

        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.approver_id.user_id.id,
            summary=f'Top-up Approval Required — {self.name}',
            note=(
                f'Top-up request <b>{self.name}</b> submitted by '
                f'<b>{self.env.user.name}</b> requires your approval.<br/>'
                f'Policy: <b>{self.policy_id.policy_number}</b><br/>'
                f'Top-up Amount: <b>\u20b9{self.amount:,.2f}</b><br/>'
                f'New Sum Insured: <b>\u20b9{self.new_sum_insured:,.2f}</b>'
            ),
        )
        self.message_post(
            body=(
                f'Top-up submitted for approval. '
                f'Approver: <b>{self.approver_id.name}</b>'
            ),
        )

    def action_approve(self):
        """Designated approver approves: finalise the top-up."""
        self.ensure_one()
        if self.approver_id.user_id != self.env.user:
            raise UserError("Only the designated approver can approve this top-up.")

        # Mark the approval activity as done
        self.activity_feedback(
            ['mail.mail_activity_data_todo'],
            feedback=f'Approved by {self.env.user.name}',
        )

        self._finalise_approval()

    def action_reject(self):
        """Designated approver rejects the top-up."""
        self.ensure_one()
        if self.approver_id.user_id != self.env.user:
            raise UserError("Only the designated approver can reject this top-up.")

        self.activity_feedback(
            ['mail.mail_activity_data_todo'],
            feedback=f'Rejected by {self.env.user.name}',
        )
        self.write({'state': 'rejected'})
        self.message_post(
            body=f'Top-up <b>rejected</b> by <b>{self.env.user.name}</b>.',
        )
        self.policy_id.message_post(
            body=(
                f'Top-up request <b>{self.name}</b> (\u20b9{self.amount:,.2f}) '
                f'was <b>rejected</b> by {self.env.user.name}.'
            ),
        )

    def action_view_payment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Top-up Payment',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reset_draft(self):
        """Reset to Draft to allow editing approver or amount."""
        self.ensure_one()
        self.write({'state': 'draft'})

    # ── Internal helpers ──────────────────────────────────────────────────────────────────

    def _finalise_approval(self):
        """Increase policy Sum Insured, create draft payment, notify banking team."""
        self.ensure_one()
        policy = self.policy_id
        old_amount = policy.initial_sum_insured
        new_amount = old_amount + self.amount

        # Update the policy limit and flag that a top-up has occurred
        policy.write({
            'initial_sum_insured': new_amount,
            'topup_flag': True,
        })

        # Log a chatter message on the policy
        policy.message_post(
            body=(
                f'<b>Sum Insured updated via Top-up {self.name}</b><br/>'
                f'Previous Sum Insured: \u20b9{old_amount:,.2f}<br/>'
                f'Top-up Amount added: \u20b9{self.amount:,.2f}<br/>'
                f'<b>New Sum Insured: \u20b9{new_amount:,.2f}</b>'
            ),
            subtype_xmlid='mail.mt_note',
        )

        # Unmark previous "latest" top-up flag
        policy.topup_ids.filtered(
            lambda t: t.id != self.id and t.is_latest
        ).write({'is_latest': False})

        # Create draft account.payment
        payment = self._create_topup_payment()

        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
            'is_latest': True,
            'payment_id': payment.id if payment else False,
        })

        self.message_post(
            body=(
                f'Top-up approved by <b>{self.env.user.name}</b>. '
                f'Sum Insured updated to <b>\u20b9{new_amount:,.2f}</b>. '
                f'Draft payment created.'
            ),
        )

        # Notify banking team to post the payment
        if payment:
            self._notify_banking_team(payment)

    def _create_topup_payment(self):
        """Create a draft account.payment for the top-up premium."""
        self.ensure_one()
        if not self.journal_id:
            return False
        try:
            payment = self.env['account.payment'].create({
                'payment_type': 'outbound',
                'amount': self.amount,
                'date': self.payment_date or fields.Date.today(),
                'journal_id': self.journal_id.id,
                'ref': (
                    f'Top-up {self.name} — '
                    f'Policy {self.policy_id.policy_number}'
                ),
                'company_id': self.policy_id.company_id.id,
                'currency_id': self.policy_id.currency_id.id,
                'is_insurance_payment': True,
                'is_topup': True,
                'insurance_policy_id': self.policy_id.id,
            })
            return payment
        except Exception:
            return False

    def _notify_banking_team(self, payment):
        """Create a To-Do activity for every user in the accounting group."""
        banking_group = self.env.ref('account.group_account_user', raise_if_not_found=False)
        users = banking_group.users if banking_group else self.env['res.users']
        if not users:
            users = self.env.ref('base.user_admin')

        pay_ref = payment.name or payment.ref or self.name
        note = (
            f'Top-up request <b>{self.name}</b> has been approved.<br/>'
            f'Policy: <b>{self.policy_id.policy_number}</b><br/>'
            f'Please post the following draft payment and then notify the requestor:<br/>'
            f'• {pay_ref} (\u20b9{self.amount:,.2f})'
        )
        for user in users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=f'Top-up Payment Ready to Post — {self.name}',
                note=note,
            )
