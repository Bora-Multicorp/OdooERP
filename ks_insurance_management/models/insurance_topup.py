# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
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
        ondelete='cascade',
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='policy_id.company_id',
        string='Company Name',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='policy_id.currency_id',
        store=True,
        readonly=True,
    )
    insurance_type_id = fields.Many2one(
        'insurance.type',
        related='policy_id.insurance_type_id',
        string='Insurance Type',
        readonly=True,
    )
    insurance_company_id = fields.Many2one(
        'insurance.company',
        related='policy_id.insurance_company_id',
        string='Insurance Company',
        readonly=True,
    )
    agent_id = fields.Many2one(
        'insurance.agent',
        related='policy_id.agent_id',
        string='Agent',
        readonly=True,
    )
    expiry_date = fields.Date(
        related='policy_id.expiry_date',
        string='Expiry Date',
        readonly=True,
    )
    cover_amount_words = fields.Char(
        related='policy_id.sum_insured_words',
        string='Cover Amount (in words)',
        readonly=True,
    )
    date = fields.Date(
        string='Request Date',
        default=fields.Date.today,
    )
    current_sum_insured = fields.Float(
        string='Current Sum Insured',
        help='Sum Insured prior to this top-up request.',
    )
    amount = fields.Float(
        string='Top-up Amount',
        required=True,
        tracking=True,
        help='The additional coverage amount to be added to the policy Sum Insured upon approval.',
    )
    topup_amount_words = fields.Char(
        string='Top-up Amount (in words)',
        compute='_compute_topup_amount_words',
        store=True,
        readonly=False,
    )
    new_sum_insured = fields.Float(
        string='New Sum Insured (After Top-up)',
        compute='_compute_new_sum_insured',
        store=True,
        readonly=False,
        help='Sum Insured after this top-up is approved.',
    )
    premium = fields.Float(
        string='Premium (Incl. GST)',
        help='Updated premium inclusive of GST.',
    )
    new_premium_percentage = fields.Float(
        string='Premium % (Preview)',
        compute='_compute_new_premium_percentage',
        store=True,
        digits=(16, 2),
        readonly=False,
        help='Premium as a percentage of the New Sum Insured.',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='pending', tracking=True)

    approver_id = fields.Many2one(
        'insurance.payment.approver',
        string='Approver',
        help='Approver for this top-up.',
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

    @api.depends('amount', 'currency_id')
    def _compute_topup_amount_words(self):
        for rec in self:
            if not rec.topup_amount_words:
                try:
                    from num2words import num2words
                    if not rec.amount:
                        rec.topup_amount_words = ''
                        continue
                    curr = rec.currency_id or rec.policy_id.currency_id
                    currency_name = curr.currency_unit_label or curr.name or ''
                    lang = 'en_IN' if curr.name == 'INR' else 'en'
                    rec.topup_amount_words = (
                        num2words(int(rec.amount), lang=lang).title()
                        + (f' {currency_name} Only' if currency_name else ' Only')
                    )
                except Exception:
                    rec.topup_amount_words = ''

    @api.depends('current_sum_insured', 'amount')
    def _compute_new_sum_insured(self):
        for rec in self:
            if not rec.new_sum_insured:
                rec.new_sum_insured = (rec.current_sum_insured or 0.0) + (rec.amount or 0.0)

    @api.depends('premium', 'new_sum_insured')
    def _compute_new_premium_percentage(self):
        for rec in self:
            if not rec.new_premium_percentage:
                rec.new_premium_percentage = (
                    (rec.premium / rec.new_sum_insured * 100.0)
                    if rec.new_sum_insured else 0.0
                )

    # ── ORM ──────────────────────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') in ('New', False, ''):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('insurance.topup') or 'New'
                )
            if 'policy_id' in vals and not vals.get('current_sum_insured'):
                policy = self.env['insurance.policy'].browse(vals['policy_id'])
                if policy.exists():
                    vals['current_sum_insured'] = policy.initial_sum_insured
        return super().create(vals_list)

    # ── Action to open wizard view ────────────────────────────────────────────────────────

    def action_view_topup_details(self):
        self.ensure_one()
        view_id = self.env.ref('ks_insurance_management.insurance_topup_details_wizard_form', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Top-up Details'),
            'res_model': 'insurance.topup',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(view_id.id if view_id else False, 'form')],
            'target': 'new',
            'context': {'create': False, 'edit': False},
        }

    # ── State actions ─────────────────────────────────────────────────────────────────────

    def action_submit(self):
        """Submit top-up for approval: assign an activity to the single approver."""
        self.ensure_one()
        if self.amount <= 0:
            raise UserError("Top-up amount must be greater than zero.")

        self.write({'state': 'pending'})

        if self.approver_id and self.approver_id.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.approver_id.user_id.id,
                summary=f'Top-up Approval Required — {self.name}',
                note=(
                    f'Top-up request <b>{self.name}</b> submitted by '
                    f'<b>{self.env.user.name}</b> requires your approval.<br/>'
                    f'Policy: <b>{self.policy_id.policy_number}</b><br/>'
                    f'Top-up Amount: <b>₹{self.amount:,.2f}</b><br/>'
                    f'New Sum Insured: <b>₹{self.new_sum_insured:,.2f}</b>'
                ),
            )
            if self.policy_id:
                self.policy_id._send_approval_bus_notification(
                    self.approver_id.user_id,
                    approval_type='topup',
                    extra_info={'amount': self.amount, 'premium': self.premium},
                )
        self.message_post(
            body=(
                f'Top-up submitted for approval. '
                f'Approver: <b>{self.approver_id.name if self.approver_id else "N/A"}</b>'
            ),
        )

    can_approve_reject = fields.Boolean(
        compute='_compute_can_approve_reject',
        string='Can Approve/Reject',
    )

    @api.depends_context('uid')
    @api.depends('policy_id', 'state')
    def _compute_can_approve_reject(self):
        for rec in self:
            can = False
            if rec.state == 'pending':
                policy = rec.policy_id
                if policy:
                    # Check if user is admin
                    if self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
                        can = True
                    # Check bora approval flags if present
                    elif hasattr(policy, 'bora_show_insurance_approve_button') and (
                        policy.bora_show_insurance_approve_button or policy.bora_show_insurance_reject_button
                    ):
                        can = True
                    # Check pending approver on policy or topup
                    elif policy.is_pending_approver:
                        can = True
                    elif rec.approver_id and rec.approver_id.user_id == self.env.user:
                        can = True
            rec.can_approve_reject = can

    def action_approve(self):
        """Designated approver approves: finalise the top-up via policy approval workflow."""
        self.ensure_one()
        if not self.can_approve_reject and not self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            raise UserError("Only the designated approver or an administrator can approve this top-up.")

        policy = self.policy_id
        if policy and policy.payment_status == 'requested' and policy.pending_topup_amount > 0:
            policy.action_approve_payment()
            if policy.payment_status == 'approved':
                if self.state != 'approved':
                    self.write({
                        'state': 'approved',
                        'approved_by': self.env.user.id,
                        'approved_date': fields.Datetime.now(),
                    })
            else:
                self.message_post(
                    body=f"Approved by <b>{self.env.user.name}</b>. Awaiting next approval."
                )
            return {'type': 'ir.actions.act_window_close'}

        # Mark the approval activity as done
        self.activity_feedback(
            ['mail.mail_activity_data_todo'],
            feedback=f'Approved by {self.env.user.name}',
        )
        self._finalise_approval()
        return {'type': 'ir.actions.act_window_close'}

    def action_reject(self):
        """Designated approver rejects the top-up via policy rejection workflow."""
        self.ensure_one()
        if not self.can_approve_reject and not self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            raise UserError("Only the designated approver or an administrator can reject this top-up.")

        policy = self.policy_id
        if policy and policy.payment_status == 'requested' and policy.pending_topup_amount > 0:
            res = policy.action_reject_payment()
            if isinstance(res, dict) and res.get('res_model') == 'bora.insurance.approval.reason.wizard':
                return res
            if self.state != 'rejected':
                self.write({'state': 'rejected'})
            return {'type': 'ir.actions.act_window_close'}

        self.activity_feedback(
            ['mail.mail_activity_data_todo'],
            feedback=f'Rejected by {self.env.user.name}',
        )
        self.write({'state': 'rejected'})
        self.message_post(
            body=f'Top-up <b>rejected</b> by <b>{self.env.user.name}</b>.',
        )
        if policy:
            policy.message_post(
                body=(
                    f'Top-up request <b>{self.name}</b> (₹{self.amount:,.2f}) '
                    f'was <b>rejected</b> by {self.env.user.name}.'
                ),
            )
        return {'type': 'ir.actions.act_window_close'}

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
                f'Previous Sum Insured: ₹{old_amount:,.2f}<br/>'
                f'Top-up Amount added: ₹{self.amount:,.2f}<br/>'
                f'<b>New Sum Insured: ₹{new_amount:,.2f}</b>'
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
                f'Sum Insured updated to <b>₹{new_amount:,.2f}</b>. '
                f'Draft payment created.'
            ),
        )

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
                'memo': (
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
