# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InsurancePolicyPayment(models.Model):
    """Single approval-based payment record covering both premium payments and top-ups.

    payment_type='premium' → on completion: marks policy as paid, updates total_premium_paid
    payment_type='topup'   → on completion: increases policy.initial_sum_insured
    """
    _name = 'insurance.policy.payment'
    _description = 'Insurance Policy Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', default='New', readonly=True, copy=False)

    payment_type = fields.Selection([
        ('premium', 'Premium Payment'),
        ('topup', 'Top-up'),
    ], string='Payment Type', required=True, default='premium',
        readonly=True, tracking=True,
        help='Premium Payment: regular insurance premium; marks the policy as paid.\n'
             'Top-up: adds to the Sum Insured (coverage increase).',
    )

    policy_id = fields.Many2one(
        'insurance.policy',
        string='Policy',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    company_id = fields.Many2one(related='policy_id.company_id', store=True)
    currency_id = fields.Many2one(related='policy_id.currency_id', store=True)

    current_sum_insured = fields.Float(
        string='Current Sum Insured',
        related='policy_id.initial_sum_insured',
        readonly=True,
    )
    amount = fields.Float(string='Amount', required=True, tracking=True)

    new_sum_insured = fields.Float(
        string='New Sum Insured (After Top-up)',
        compute='_compute_new_sum_insured',
        store=True,
    )

    approver_id = fields.Many2one(
        'insurance.payment.approver',
        string='Approver',
        required=True,
        tracking=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        domain=[('type', 'in', ['bank', 'cash'])],
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Pending Approval'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        readonly=True,
        copy=False,
    )
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    approved_date = fields.Datetime(readonly=True, copy=False)
    notes = fields.Text(string='Notes')

    # ── Compute ───────────────────────────────────────────────────────────────────────────

    @api.depends('policy_id.initial_sum_insured', 'amount')
    def _compute_new_sum_insured(self):
        for rec in self:
            if rec.payment_type == 'topup':
                rec.new_sum_insured = (rec.policy_id.initial_sum_insured or 0.0) + (rec.amount or 0.0)
            else:
                rec.new_sum_insured = 0.0

    # ── ORM ───────────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('insurance.policy.payment') or 'New'
                )
        return super().create(vals_list)

    # ── Actions ───────────────────────────────────────────────────────────────────────────

    def action_submit(self):
        """Submit for approval: assign an activity to the approver."""
        self.ensure_one()
        if self.amount <= 0:
            raise UserError("Amount must be greater than zero.")

        self.write({'state': 'submitted'})

        label = 'Top-up' if self.payment_type == 'topup' else 'Payment'
        policy_ref = self.policy_id.policy_number
        note_lines = [
            f'{label} request <b>{self.name}</b> submitted by <b>{self.requested_by.name}</b> '
            f'requires your approval.<br/>',
            f'Policy: <b>{policy_ref}</b><br/>',
            f'Amount: <b>\u20b9{self.amount:,.2f}</b>',
        ]
        if self.payment_type == 'topup':
            note_lines.append(
                f'<br/>Current Sum Insured: \u20b9{self.current_sum_insured:,.2f} → '
                f'New Sum Insured: <b>\u20b9{self.new_sum_insured:,.2f}</b>'
            )

        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.approver_id.user_id.id,
            summary=f'Insurance {label} Approval Required — {self.name}',
            note=''.join(note_lines),
        )
        self.message_post(
            body=f'{label} request submitted for approval. Approver: <b>{self.approver_id.name}</b>',
        )

    def action_approve(self):
        """Approver approves: create draft payment, notify banking team."""
        self.ensure_one()
        if self.approver_id.user_id != self.env.user:
            raise UserError("Only the designated approver can approve this request.")

        self.activity_feedback(
            ['mail.mail_activity_data_todo'],
            feedback=f'Approved by {self.env.user.name}',
        )

        payment = self._create_draft_payment()

        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
            'payment_id': payment.id if payment else False,
        })

        label = 'Top-up' if self.payment_type == 'topup' else 'Payment'
        self.message_post(
            body=(
                f'{label} approved by <b>{self.env.user.name}</b>. '
                f'Draft payment created. Banking team notified.'
            ),
        )

        if payment:
            self._notify_banking_team(payment)

    def action_mark_paid(self):
        """Banking team confirms payment is posted."""
        self.ensure_one()
        self.activity_feedback(
            ['mail.mail_activity_data_todo'],
            feedback='Payment posted and confirmed.',
        )
        self.write({'state': 'paid'})
        self._apply_payment_effect()
        self._notify_insurance_team()
        self.message_post(body='Payment marked as <b>Paid</b>. Insurance team notified.')

    def action_reject(self):
        """Approver rejects the request."""
        self.ensure_one()
        if self.approver_id.user_id != self.env.user:
            raise UserError("Only the designated approver can reject this request.")
        self.activity_feedback(
            ['mail.mail_activity_data_todo'],
            feedback=f'Rejected by {self.env.user.name}',
        )
        self.write({'state': 'rejected'})
        self.message_post(body=f'Request <b>rejected</b> by <b>{self.env.user.name}</b>.')

    def action_reset_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_view_payment(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payment',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Helpers ───────────────────────────────────────────────────────────────────────────

    def _create_draft_payment(self):
        self.ensure_one()
        if not self.journal_id:
            return False
        label = 'Top-up' if self.payment_type == 'topup' else 'Premium'
        policy_ref = self.policy_id.policy_number
        try:
            payment = self.env['account.payment'].create({
                'payment_type': 'outbound',
                'amount': self.amount,
                'date': fields.Date.today(),
                'journal_id': self.journal_id.id,
                'ref': f'{label} {self.name} — Policy {policy_ref}',
                'company_id': self.policy_id.company_id.id,
                'currency_id': self.policy_id.currency_id.id,
                'is_insurance_payment': True,
                'is_topup': self.payment_type == 'topup',
                'insurance_policy_id': self.policy_id.id,
            })
            return payment
        except Exception:
            _logger.exception("Failed to create draft payment for %s", self.name)
            return False

    def _apply_payment_effect(self):
        """After banking confirms: update policy fields based on payment type."""
        self.ensure_one()
        policy = self.policy_id
        if self.payment_type == 'premium':
            policy.write({
                'payment_status': 'paid',
                'is_paid': True,
            })
        elif self.payment_type == 'topup':
            old = policy.initial_sum_insured
            new = old + self.amount
            policy.write({
                'initial_sum_insured': new,
                'topup_flag': True,
            })
            # Mark this as the latest top-up (clear old flags)
            policy.policy_payment_ids.filtered(
                lambda r: r.id != self.id and r.payment_type == 'topup' and r.state == 'paid'
            ).write({'is_latest_topup': False})
            self.is_latest_topup = True
            policy.message_post(
                body=(
                    f'<b>Sum Insured updated via Top-up {self.name}</b><br/>'
                    f'Previous: \u20b9{old:,.2f} → New: <b>\u20b9{new:,.2f}</b>'
                ),
                subtype_xmlid='mail.mt_note',
            )

    def _notify_banking_team(self, payment):
        """Assign a To-Do activity to every user in the accounting group."""
        banking_group = self.env.ref('account.group_account_user', raise_if_not_found=False)
        users = banking_group.users if banking_group else self.env['res.users']
        if not users:
            users = self.env.ref('base.user_admin')

        label = 'Top-up' if self.payment_type == 'topup' else 'Premium'
        policy_ref = self.policy_id.policy_number
        pay_ref = payment.name or getattr(payment, 'memo', '') or self.name
        note = (
            f'Insurance {label.lower()} request <b>{self.name}</b> has been approved.<br/>'
            f'Policy: <b>{policy_ref}</b><br/>'
            f'Please post the following draft payment:<br/>'
            f'• {pay_ref} (\u20b9{self.amount:,.2f})<br/>'
            f'Then click <b>Mark as Paid</b> on the request.'
        )
        for user in users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=f'Insurance {label} Payment Ready to Post — {self.name}',
                note=note,
            )

    def _notify_insurance_team(self):
        """Notify insurance users that payment is complete."""
        ins_group = self.env.ref(
            'ks_insurance_management.group_insurance_user', raise_if_not_found=False)
        if not ins_group:
            return
        label = 'Top-up' if self.payment_type == 'topup' else 'Premium'
        policy_ref = self.policy_id.policy_number
        for user in ins_group.users.filtered(lambda u: u.id != self.requested_by.id):
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=f'Insurance {label} Payment Completed — {self.name}',
                note=(
                    f'{label} payment <b>{self.name}</b> for policy <b>{policy_ref}</b> '
                    f'has been fully processed. Amount: \u20b9{self.amount:,.2f}'
                ),
            )
