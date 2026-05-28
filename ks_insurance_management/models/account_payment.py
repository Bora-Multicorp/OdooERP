# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # ── Insurance-specific fields ─────────────────────────────────────────────

    is_topup = fields.Boolean(
        string='Is Top-up',
        default=False,
        copy=False,
        help='True when this payment is for a policy top-up (coverage increase).',
    )
    is_insurance_payment = fields.Boolean(
        string='Insurance Payment',
        default=False,
        help='Marks this as an insurance premium or top-up payment.',
    )
    insurance_policy_id = fields.Many2one(
        'insurance.policy',
        string='Insurance Policy',
        copy=False,
        help='The insurance policy linked to this payment.',
    )

    # ── Fields used by the Insurance Details popup (payment → new policy) ─────

    insurance_popup_done = fields.Boolean(default=False, copy=False)
    ins_company_id = fields.Many2one('res.company', string='Insured Company')
    ins_type_id = fields.Many2one('insurance.type', string='Insurance Type')
    ins_policy_number = fields.Char(string='Policy Number')
    ins_sum_insured = fields.Float(string='Sum Insured')
    ins_sum_insured_words = fields.Char(
        string='Cover Amount (in Words)',
        compute='_compute_ins_words',
        store=True,
    )
    ins_agent = fields.Char(string='Agent Name')
    ins_insurance_company_id = fields.Many2one('insurance.company', string='Insurance Company')
    ins_expiry_date = fields.Date(string='Expiry Date')
    ins_policy_type = fields.Selection(
        [('individual', 'Individual'), ('floater', 'Floater')],
        string='Policy Type',
    )
    ins_floater_location_ids = fields.Many2many('stock.warehouse', string='Covered Locations (Floater)')

    # ── Compute ───────────────────────────────────────────────────────────────

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

    # ── Override action_post to update policy on payment confirmation ─────────

    def action_post(self):
        result = super().action_post()
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
            else:
                # Regular premium payment confirmed: mark paid and activate policy
                policy.write({
                    'payment_status': 'paid',
                    'is_paid': True,
                    'state': 'active',
                })
            # Notify the insurance team
            policy._notify_insurance_team()
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
