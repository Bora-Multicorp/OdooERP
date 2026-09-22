# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InsurancePolicy(models.Model):
    _inherit = 'insurance.policy'

    # ── Approval tracking fields ──────────────────────────────────────────────
    bora_insurance_pm1_id = fields.Many2one('res.users', string='Payment Approver PM1', copy=False)
    bora_insurance_pm2_id = fields.Many2one('res.users', string='Payment Approver PM2', copy=False)
    bora_insurance_pm1_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_insurance_pm2_approved = fields.Boolean(default=False, copy=False, tracking=True)
    bora_insurance_request_reason = fields.Text(string='Request Reason', copy=False)
    bora_insurance_request_user_id = fields.Many2one('res.users', string='Requested By', copy=False)
    bora_insurance_request_date = fields.Datetime(string='Request Date', copy=False)

    # ── Computed UI fields ────────────────────────────────────────────────────
    bora_is_insurance_pm_user = fields.Boolean(compute='_compute_bora_insurance_pm_user')
    bora_is_insurance_admin = fields.Boolean(compute='_compute_bora_insurance_admin')
    bora_is_insurance_dual_approval = fields.Boolean(compute='_compute_bora_insurance_dual_approval')

    bora_show_insurance_approve_button = fields.Boolean(compute='_compute_insurance_button_visibility')
    bora_show_insurance_reject_button = fields.Boolean(compute='_compute_insurance_button_visibility')
    bora_show_insurance_update_button = fields.Boolean(compute='_compute_insurance_button_visibility')

    # ─────────────────────────────────────────────────────────────────────────
    # Config helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _get_insurance_approval_config(self):
        config = self.env['bora.insurance.approval.config'].get_config(
            company=self.company_id
        )
        if not config:
            raise UserError(_(
                'No active insurance payment approval configuration found for company "%s". '
                'Please configure approvers in Insurance > Configuration > '
                'Approval Authorities.'
            ) % self.company_id.name)
        return config

    def _has_insurance_approval_config(self):
        return bool(
            self.env['bora.insurance.approval.config'].get_config(
                company=self.company_id
            )
        )

    def _is_insurance_admin_user(self):
        """Returns True if user is Insurance Admin or system admin."""
        return (
            self.env.user.has_group('ks_insurance_management.group_insurance_admin')
            or self.env.user._is_admin()
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Computed fields
    # ─────────────────────────────────────────────────────────────────────────
    @api.depends_context('uid')
    def _compute_bora_insurance_admin(self):
        is_admin = self._is_insurance_admin_user()
        for rec in self:
            rec.bora_is_insurance_admin = is_admin

    @api.depends_context('uid')
    def _compute_bora_insurance_pm_user(self):
        for rec in self:
            if rec._has_insurance_approval_config():
                config = rec._get_insurance_approval_config()
                rec.bora_is_insurance_pm_user = self.env.user in config.get_all_pm_users()
            else:
                rec.bora_is_insurance_pm_user = False

    @api.depends('payment_status')
    def _compute_bora_insurance_dual_approval(self):
        for rec in self:
            if rec._has_insurance_approval_config():
                rec.bora_is_insurance_dual_approval = (
                    rec._get_insurance_approval_config().is_dual_approval()
                )
            else:
                rec.bora_is_insurance_dual_approval = False

    @api.depends(
        'payment_status',
        'bora_is_insurance_pm_user',
        'bora_insurance_pm1_id', 'bora_insurance_pm2_id',
        'bora_insurance_pm1_approved', 'bora_insurance_pm2_approved',
        'bora_insurance_request_user_id',
    )
    @api.depends_context('uid')
    def _compute_insurance_button_visibility(self):
        current_user = self.env.user
        for rec in self:
            rec.bora_show_insurance_approve_button = False
            rec.bora_show_insurance_reject_button = False
            rec.bora_show_insurance_update_button = False

            if rec.payment_status != 'requested':
                continue

            is_admin = rec._is_insurance_admin_user()
            is_pm = rec.bora_is_insurance_pm_user

            if is_admin:
                rec.bora_show_insurance_approve_button = True
                rec.bora_show_insurance_reject_button = True
                rec.bora_show_insurance_update_button = True
                continue

            if not rec._has_insurance_approval_config():
                continue

            if not is_pm:
                # Original requester can update approvers while pending
                if rec.bora_insurance_request_user_id == current_user:
                    rec.bora_show_insurance_update_button = True

            if is_pm:
                # PM1 can approve if not yet done
                if (rec.bora_insurance_pm1_id and current_user == rec.bora_insurance_pm1_id
                        and not rec.bora_insurance_pm1_approved):
                    rec.bora_show_insurance_approve_button = True
                    rec.bora_show_insurance_reject_button = True

                # PM2 can approve if PM1 approved and PM2 not yet done
                elif (rec.bora_insurance_pm2_id and current_user == rec.bora_insurance_pm2_id
                      and rec.bora_insurance_pm1_approved
                      and not rec.bora_insurance_pm2_approved):
                    rec.bora_show_insurance_approve_button = True
                    rec.bora_show_insurance_reject_button = True

                # Current approver or requester can update approver selection
                if ((rec.bora_insurance_pm1_id == current_user and not rec.bora_insurance_pm1_approved)
                        or (rec.bora_insurance_pm2_id == current_user and rec.bora_insurance_pm1_approved and not rec.bora_insurance_pm2_approved)
                        or rec.bora_insurance_request_user_id == current_user):
                    rec.bora_show_insurance_update_button = True

    # ─────────────────────────────────────────────────────────────────────────
    # Workflow Actions
    # ─────────────────────────────────────────────────────────────────────────
    def action_request_payment(self):
        """Open approval request wizard on payment request."""
        # Ensure config exists for company
        self._get_insurance_approval_config()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Request Approval Authorities'),
            'res_model': 'bora.insurance.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bora_policy_ids': [(6, 0, self.ids)],
            },
        }

    def action_update_approvers(self):
        """Open approval request wizard in update mode."""
        self.ensure_one()
        self._get_insurance_approval_config()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Update Approval Authorities'),
            'res_model': 'bora.insurance.approval.request.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'bora_is_update': True,
                'default_bora_policy_ids': [(6, 0, self.ids)],
            },
        }

    def bora_do_request_insurance_approval(self, pm1_user, pm2_user=None, reason=None):
        """Submit policies for approval with selected approvers."""
        activity_type = self.env.ref(
            'bora_insurance_approval.mail_activity_data_insurance_approval',
            raise_if_not_found=False
        )
        act_type_id = activity_type.id if activity_type else False

        for rec in self:
            rec.write({
                'payment_status': 'requested',
                'bora_insurance_pm1_id': pm1_user.id if pm1_user else False,
                'bora_insurance_pm2_id': pm2_user.id if pm2_user else False,
                'bora_insurance_pm1_approved': False,
                'bora_insurance_pm2_approved': False,
                'bora_insurance_request_reason': reason or '',
                'bora_insurance_request_user_id': self.env.user.id,
                'bora_insurance_request_date': fields.Datetime.now(),
            })

            # Schedule activity for PM1
            rec._create_insurance_approval_activity(pm1_user, 'Confirm')

            msg = _(
                'Insurance approval requested by <b>%s</b>.<br/>'
                'Awaiting Approver 1 approval: <b>%s</b>.'
            ) % (self.env.user.name, pm1_user.name)
            if pm2_user:
                msg += _('<br/>Approver 2: <b>%s</b>.') % pm2_user.name
            if reason:
                msg += _('<br/>Reason: %s') % reason

            rec.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')

    def action_approve_payment(self):
        """Approve payment request (PM1 or PM2 step, or Admin override)."""
        current_user = self.env.user
        for rec in self:
            if rec.payment_status != 'requested':
                raise UserError(_("This policy does not have a pending payment request."))

            config = rec._get_insurance_approval_config()
            is_admin = rec._is_insurance_admin_user()
            is_dual = config.is_dual_approval()

            # Case 1: PM1 approval step
            if not rec.bora_insurance_pm1_approved:
                if not is_admin and current_user != rec.bora_insurance_pm1_id:
                    raise UserError(_("Only Approver 1 (%s) or an Administrator can perform this approval.")
                                    % (rec.bora_insurance_pm1_id.name if rec.bora_insurance_pm1_id else 'N/A'))

                rec.write({'bora_insurance_pm1_approved': True})
                rec._bora_unlink_user_activity(rec.bora_insurance_pm1_id)

                if is_dual and rec.bora_insurance_pm2_id:
                    # Create PM2 activity
                    rec._create_insurance_approval_activity(rec.bora_insurance_pm2_id, 'Confirm')
                    msg = _('Approved by Approver 1 (%s). Now awaiting Approver 2 (%s) approval.') % (
                        current_user.name, rec.bora_insurance_pm2_id.name
                    )
                    rec.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')
                    continue  # Await PM2 approval

            # Case 2: PM2 approval step (or Single Mode completed, or Admin approving)
            if is_dual and rec.bora_insurance_pm2_id and not rec.bora_insurance_pm2_approved:
                if not is_admin and current_user != rec.bora_insurance_pm2_id:
                    raise UserError(_("Only Approver 2 (%s) or an Administrator can perform this approval.")
                                    % rec.bora_insurance_pm2_id.name)

                rec.write({'bora_insurance_pm2_approved': True})
                rec._bora_unlink_user_activity(rec.bora_insurance_pm2_id)

            # Both approvals complete or single mode complete! Mark approved & proceed with draft payment creation
            rec._bora_cancel_insurance_activities()
            rec._bora_do_complete_payment_approval()

    def _bora_do_complete_payment_approval(self):
        """Execute final approval logic (creating payment and updating status)."""
        for rec in self:
            is_topup = bool(rec.pending_topup_amount > 0 or rec.pending_topup_premium > 0)
            amount = rec.pending_topup_premium if (is_topup and rec.pending_topup_premium) else rec.premium
            if not amount:
                raise UserError(_(
                    "No payment amount found. "
                    "Please set a Premium on the policy or re-submit the top-up request."
                ))

            journal = rec.env['account.journal'].search([
                ('type', 'in', ['bank', 'cash']),
                ('company_id', '=', rec.company_id.id),
            ], limit=1)
            if not journal:
                raise UserError(_(
                    "No bank or cash journal found for company '%s'. "
                    "Please configure one in Accounting → Configuration → Journals."
                ) % rec.company_id.name)

            memo = f"Top-up Premium for {rec.policy_number}" if is_topup else f"Premium Payment — {rec.policy_number}"
            
            partner = False
            if rec.insurance_company_id:
                partner = rec.env['res.partner'].search([
                    ('name', '=', rec.insurance_company_id.name),
                ], limit=1)
                if not partner:
                    partner = rec.env['res.partner'].sudo().create({
                        'name': rec.insurance_company_id.name,
                        'is_company': True,
                        'supplier_rank': 1,
                    })

            payment_vals = {
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': partner.id if partner else False,
                'amount': amount,
                'currency_id': rec.company_id.currency_id.id,
                'journal_id': journal.id,
                'memo': memo,
                'company_id': rec.company_id.id,
                'is_insurance_payment': True,
                'insurance_policy_id': rec.id,
                'is_topup': is_topup,
            }
            payment = rec.env['account.payment'].create(payment_vals)

            rec.write({
                'payment_status': 'approved',
                'payment_ids': [(4, payment.id)],
            })
            rec._notify_banking_team(payment)
            rec.message_post(
                body=_(
                    "Payment request <b>APPROVED</b>. Draft payment <b>%s</b> "
                    "created for ₹%s and sent to the accounting team for posting."
                ) % (payment.name or 'Draft Payment', f"{payment.amount:,.2f}")
            )

    def action_reject_payment(self):
        """Open rejection reason wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Insurance Payment Request'),
            'res_model': 'bora.insurance.approval.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bora_policy_id': self.id,
                'default_bora_action_type': 'reject',
            },
        }

    def bora_do_reject_insurance(self, reason):
        """Perform rejection rollout."""
        for rec in self:
            rec._bora_cancel_insurance_activities()

            vals = {}
            if rec.pending_topup_amount > 0:
                completed_topups = rec.payment_ids.filtered(
                    lambda p: p.is_topup and p.state == 'posted'
                )
                vals.update({
                    'pending_topup_amount': 0.0,
                    'topup_flag': bool(completed_topups),
                })

            vals.update({
                'payment_status': 'paid' if rec.is_paid else 'draft',
                'bora_insurance_pm1_id': False,
                'bora_insurance_pm2_id': False,
                'bora_insurance_pm1_approved': False,
                'bora_insurance_pm2_approved': False,
                'pending_topup_approver_id': False,
                'pending_payment_approver_id': False,
                'pending_topup_premium': 0.0,
            })
            rec.write(vals)

            rec.message_post(
                body=_("Insurance payment request <b>REJECTED</b> by <b>%s</b>.<br/>Reason: %s") % (
                    self.env.user.name, reason
                ),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Activity & Notification Helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _create_insurance_approval_activity(self, user, action_name='Confirm'):
        self.ensure_one()
        activity_type = self.env.ref(
            'bora_insurance_approval.mail_activity_data_insurance_approval',
            raise_if_not_found=False
        )
        act_type_id = activity_type.id if activity_type else self.env.ref('mail.mail_activity_data_todo').id
        self.env['mail.activity'].create({
            'activity_type_id': act_type_id,
            'note': _('Insurance Approval requested for Policy %s.') % self.policy_number,
            'res_id': self.id,
            'res_model_id': self.env.ref('ks_insurance_management.model_insurance_policy').id,
            'user_id': user.id,
            'summary': _('Insurance Approval required'),
        })

    def _bora_unlink_user_activity(self, user):
        self.ensure_one()
        if not user:
            return
        activities = self.env['mail.activity'].sudo().search([
            ('res_model', '=', 'insurance.policy'),
            ('res_id', '=', self.id),
            ('user_id', '=', user.id),
        ])
        activities.unlink()

    def _bora_cancel_insurance_activities(self):
        for rec in self:
            activities = self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'insurance.policy'),
                ('res_id', '=', rec.id),
            ])
            activities.unlink()
