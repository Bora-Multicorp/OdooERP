# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ── Insurance-specific fields ─────────────────────────────────────────────

    is_topup = fields.Boolean(
        string='Is Top-up',
        default=False,
        copy=False,
        help='True when this payment is for a policy top-up (coverage increase).',
    )
    is_renewal = fields.Boolean(
        string='Is Renewal',
        default=False,
        copy=False,
        help='True when this payment is for a policy renewal.',
    )
    is_insurance_payment = fields.Boolean(
        string='Insurance Payment',
        default=False,
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
        help='Marks this as an insurance premium or top-up payment.',
    )
    insurance_policy_id = fields.Many2one(
        'insurance.policy',
        string='Insurance Policy',
        copy=False,
        help='The insurance policy linked to this payment.',
    )
    ks_insurance_draft_notified = fields.Boolean(
        string='Approver 2 Notified for Draft Payment',
        default=False,
        copy=False,
        help='Technical field to prevent duplicate draft payment notifications to Approver 2 users.',
    )

    # ── Fields used by the Insurance Details popup (payment → new policy) ─────

    insurance_popup_done = fields.Boolean(default=False, copy=False)
    ins_company_id = fields.Many2one(
        'res.company',
        string='Insured Company',
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
    )
    ins_type_id = fields.Many2one(
        'insurance.type',
        string='Insurance Type',
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
    )
    ins_policy_number = fields.Char(
        string='Policy Number',
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
    )
    ins_sum_insured = fields.Float(
        string='Sum Insured',
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
    )
    ins_sum_insured_words = fields.Char(
        string='Cover Amount (in Words)',
        compute='_compute_ins_words',
        store=True,
    )
    ins_agent = fields.Char(
        string='Agent Name',
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
    )
    ins_insurance_company_id = fields.Many2one(
        'insurance.company',
        string='Insurance Company',
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
    )
    ins_expiry_date = fields.Date(
        string='Expiry Date',
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
    )
    ins_policy_type = fields.Selection(
        [('individual', 'Individual'), ('floater', 'Floater')],
        string='Policy Type',
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
    )
    ins_floater_location_ids = fields.Many2many(
        'stock.warehouse',
        string='Covered Locations (Floater)',
        compute='_compute_ins_fields_from_policy',
        store=True,
        readonly=False,
        precompute=True,
    )

    # ── Compute ───────────────────────────────────────────────────────────────

    @api.depends(
        'insurance_policy_id',
        'insurance_policy_id.company_id',
        'insurance_policy_id.insurance_type_id',
        'insurance_policy_id.policy_number',
        'insurance_policy_id.initial_sum_insured',
        'insurance_policy_id.agent_id',
        'insurance_policy_id.insurance_company_id',
        'insurance_policy_id.expiry_date',
        'insurance_policy_id.policy_type',
        'insurance_policy_id.floater_location_ids',
    )
    def _compute_ins_fields_from_policy(self):
        for rec in self:
            if rec.insurance_policy_id:
                policy = rec.insurance_policy_id
                rec.is_insurance_payment = True
                rec.ins_company_id = policy.company_id
                rec.ins_type_id = policy.insurance_type_id
                rec.ins_policy_number = policy.policy_number
                rec.ins_sum_insured = policy.initial_sum_insured
                rec.ins_agent = policy.agent_id.name if policy.agent_id else False
                rec.ins_insurance_company_id = policy.insurance_company_id
                rec.ins_expiry_date = policy.expiry_date
                rec.ins_policy_type = policy.policy_type
                rec.ins_floater_location_ids = policy.floater_location_ids
            elif not rec.is_insurance_payment:
                rec.is_insurance_payment = False

    @api.depends('ins_sum_insured')
    def _compute_ins_words(self):
        for rec in self:
            try:
                from num2words import num2words
                rec.ins_sum_insured_words = (
                    num2words(int(rec.ins_sum_insured), lang='en_IN').title() + ' Rupees Only'
                ) if rec.ins_sum_insured else ''
            except Exception:
                rec.ins_sum_insured_words = ''

    # ── Prevent deletion of insurance-linked payments ────────────────────────

    def unlink(self):
        for payment in self:
            if payment.insurance_policy_id or payment.is_insurance_payment:
                raise UserError(
                    "Payment '%s' is linked to an insurance policy and cannot be deleted." % payment.name
                )
        return super().unlink()

    # ── Validation for insurance payments ────────────────────────────────────

    @api.constrains('is_insurance_payment', 'partner_id', 'amount')
    def _check_insurance_payment_fields(self):
        for rec in self:
            if not rec.is_insurance_payment:
                continue
            # if not rec.partner_id:
            #     raise UserError("Customer is required for insurance payments.")
            if rec.amount <= 0:
                raise UserError("Amount must be greater than zero for insurance payments.")

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        for payment in payments:
            if payment.insurance_policy_id:
                policy = payment.insurance_policy_id
                if payment.is_renewal or policy.state == 'under_renewal':
                    pending_hist = policy.renewal_history_ids.filtered(
                        lambda r: not r.is_policy_number_updated and not r.payment_id
                    )
                    if pending_hist:
                        pending_hist[:1].payment_id = payment.id
                if payment.is_topup:
                    pending_topup = policy.topup_ids.filtered(
                        lambda t: not t.payment_id and t.state in ('draft', 'pending', 'approved')
                    )
                    if pending_topup:
                        pending_topup[:1].write({
                            'payment_id': payment.id,
                            'payment_date': payment.date,
                            'state': 'approved',
                        })
            if payment.state == 'draft' and (payment.is_insurance_payment or payment.insurance_policy_id):
                payment._notify_insurance_draft_payment()
        return payments

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_insurance_payment') or vals.get('insurance_policy_id'):
            for payment in self:
                if payment.state == 'draft' and not payment.ks_insurance_draft_notified and (payment.is_insurance_payment or payment.insurance_policy_id):
                    payment._notify_insurance_draft_payment()
        if vals.get('state') in ('posted', 'paid'):
            self._apply_payment_confirmed()
        return res

    def _notify_insurance_draft_payment(self):
        """Notify all users configured in Approver 2 Users of Global Vendor Payment Approval Configuration
        when a new draft insurance payment is created/generated automatically.
        """
        if 'vendor.payment.approval.config' not in self.env:
            return
        config_model = self.env['vendor.payment.approval.config']

        config = config_model.sudo().search([('active', '=', True)], limit=1)
        if not config or not config.ks_approver_2_ids:
            return

        approver_2_users = config.ks_approver_2_ids.filtered(lambda u: u.active and not u.share)
        if not approver_2_users:
            return

        todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        approver_2_partners = approver_2_users.mapped('partner_id')

        for payment in self:
            if payment.state != 'draft' or payment.ks_insurance_draft_notified:
                continue
            if not (payment.is_insurance_payment or payment.insurance_policy_id):
                continue

            policy = payment.insurance_policy_id
            policy_num = policy.policy_number if policy and policy.policy_number else ''
            ins_type_name = payment.ins_type_id.name or (policy.insurance_type_id.name if policy and policy.insurance_type_id else '')
            company_name = payment.ins_company_id.name or payment.company_id.name or ''
            partner_name = payment.partner_id.name or (policy.insurance_company_id.name if policy and policy.insurance_company_id else '')
            memo_val = payment.memo or ''

            display_name = payment.name or memo_val or _('Draft Payment')
            summary = _('Insurance Draft Payment: %s') % display_name
            policy_line = f" for policy <b>{policy_num}</b>" if policy_num else ""
            if ins_type_name:
                policy_line += f" ({ins_type_name})"

            note = _(
                'A new draft insurance payment <b>%(payment)s</b> has been generated%(policy_line)s.<br/>'
                '<b>Company:</b> %(company)s<br/>'
                '<b>Vendor / Insurance Company:</b> %(partner)s<br/>'
                '<b>Amount:</b> ₹%(amount)s<br/>'
                '<b>Memo:</b> %(memo)s'
            ) % {
                'payment': display_name,
                'policy_line': policy_line,
                'company': company_name,
                'partner': partner_name,
                'amount': f"{payment.amount:,.2f}",
                'memo': memo_val,
            }

            plain_message = _(
                'Draft insurance payment %(payment)s created for ₹%(amount)s%(policy_info)s. Memo: %(memo)s'
            ) % {
                'payment': display_name,
                'amount': f"{payment.amount:,.2f}",
                'policy_info': f" (Policy: {policy_num})" if policy_num else "",
                'memo': memo_val,
            }

            # 1. Schedule Activity for Approver 2 users on the payment
            for user in approver_2_users:
                existing_act = payment.activity_ids.filtered(
                    lambda a: a.user_id == user and (not todo_type or a.activity_type_id == todo_type)
                )
                if not existing_act:
                    try:
                        payment.activity_schedule(
                            'mail.mail_activity_data_todo',
                            user_id=user.id,
                            summary=summary,
                            note=note,
                        )
                    except Exception as e:
                        _logger.warning("Failed to schedule activity for Approver 2 user %s on payment %s: %s", user.id, payment.id, e)

                # 2. Real-time Bus Notification for Approver 2 users
                try:
                    self.env['bus.bus']._sendone(
                        user.partner_id,
                        'simple_notification',
                        {
                            'type': 'info',
                            'title': summary,
                            'message': plain_message,
                            'sticky': True,
                        },
                    )
                except Exception as e:
                    _logger.warning("Failed to send bus notification to user %s: %s", user.id, e)

            # 3. Post Chatter Message on payment record
            try:
                payment.message_post(
                    body=note,
                    subject=summary,
                    partner_ids=approver_2_partners.ids,
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
            except Exception as e:
                _logger.warning("Failed to post message on payment %s: %s", payment.id, e)

            # 4. Post Chatter Message on linked insurance policy
            if policy:
                try:
                    policy.message_post(
                        body=note,
                        subject=summary,
                        partner_ids=approver_2_partners.ids,
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment',
                    )
                except Exception as e:
                    _logger.warning("Failed to post message on policy %s: %s", policy.id, e)

            payment.ks_insurance_draft_notified = True

    # ── Override action_post to update policy on payment confirmation ─────────

    def _apply_payment_confirmed(self):
        for payment in self:
            policy = payment.insurance_policy_id
            if not policy:
                continue
            if payment.is_topup:
                # Top-up payment confirmed: add topup to sum insured, update premium
                update_vals = {
                    'topup_flag': True,
                    'initial_sum_insured': policy.initial_sum_insured + policy.pending_topup_amount,
                    'pending_topup_amount': 0.0,
                    'payment_status': 'paid',
                }
                if policy.pending_topup_premium:
                    update_vals['premium'] = policy.pending_topup_premium
                    update_vals['pending_topup_premium'] = 0.0
                policy.write(update_vals)
                topups = policy.topup_ids.filtered(lambda t: t.payment_id == payment)
                if topups:
                    policy.topup_ids.filtered(lambda t: t.id not in topups.ids and t.is_latest).write({'is_latest': False})
                    topups.write({'state': 'approved', 'is_latest': True})
            elif payment.is_renewal or policy.state == 'under_renewal':
                # Renewal payment confirmed: mark paid and activate policy
                policy.write({
                    'payment_status': 'approved',
                    'is_paid': True,
                    'state': 'active',
                })
            else:
                # Regular premium payment confirmed: mark paid, activate policy, and set start_date to payment date
                policy_vals = {
                    'payment_status': 'approved',
                    'is_paid': True,
                    'state': 'active',
                }
                if payment.date:
                    policy_vals['start_date'] = payment.date
                policy.write(policy_vals)
            # Notify the insurance team
            policy._notify_insurance_team()

    def action_post(self):
        result = super().action_post()
        self._apply_payment_confirmed()
        return result

    # ── Insurance Details popup (existing popup wizard flow) ──────────────────

    def action_open_insurance_popup(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Insurance Details',
            'res_model': 'insurance.payment.popup.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payment_id': self.id,
                'default_premium': self.amount,
                'default_company_id': self.company_id.id,
            },
        }

    def _create_insurance_policy(self):
        self.ensure_one()
        agent_id = False
        if self.ins_agent:
            agent = self.env['insurance.agent'].search([('name', 'ilike', self.ins_agent)], limit=1)
            if not agent:
                agent = self.env['insurance.agent'].create({'name': self.ins_agent})
            agent_id = agent.id
        policy_vals = {
            'company_id': self.ins_company_id.id or self.company_id.id,
            'currency_id': (self.ins_company_id or self.company_id).currency_id.id,
            'insurance_type_id': self.ins_type_id.id,
            'insurance_company_id': self.ins_insurance_company_id.id,
            'agent_id': agent_id,
            'policy_number': self.ins_policy_number,
            'initial_sum_insured': self.ins_sum_insured,
            'premium': self.amount,
            'expiry_date': self.ins_expiry_date,
            'policy_type': self.ins_policy_type or 'individual',
            'floater_location_ids': [(6, 0, self.ins_floater_location_ids.ids)],
            'payment_id': self.id,
            'insurance_policy_id': self.id,
            # Created directly from payment → mark as paid
            'state': 'active',
            'payment_status': 'paid',
            'is_paid': True,
        }
        policy = self.env['insurance.policy'].create(policy_vals)
        self.insurance_policy_id = policy.id
        self.insurance_popup_done = True
        return policy
