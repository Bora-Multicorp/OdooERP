# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InsurancePolicyRenewWizard(models.TransientModel):
    _name = 'insurance.policy.renew.wizard'
    _description = 'Renew Insurance Policy Wizard'

    policy_id = fields.Many2one(
        'insurance.policy',
        string='Policy',
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related='policy_id.company_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='policy_id.currency_id',
        readonly=True,
    )
    current_policy_number = fields.Char(
        string='Current Policy Number',
        related='policy_id.policy_number',
        readonly=True,
    )
    insurance_type_id = fields.Many2one(
        related='policy_id.insurance_type_id',
        string='Insurance Type',
        readonly=True,
    )
    current_expiry_date = fields.Date(
        string='Current Expiry Date',
        related='policy_id.expiry_date',
        readonly=True,
    )
    renewal_premium = fields.Float(
        string='Renewal Premium (Incl. GST)',
        required=True,
        help='Premium amount inclusive of GST for the renewed period.',
    )
    new_start_date = fields.Date(
        string='New Start Date',
        required=True,
        help='Start date for the renewed policy period.',
    )
    new_expiry_date = fields.Date(
        string='New Expiry Date',
        required=True,
        help='Expiry date for the renewed policy period.',
    )
    new_sum_insured = fields.Float(
        string='Sum Insured',
        required=True,
        help='Sum insured coverage limit for the renewed period.',
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        required=True,
        domain="[('type', 'in', ['bank', 'cash']), ('company_id', '=', company_id)]",
        help='Bank or Cash journal for the renewal payment.',
    )
    notes = fields.Text(string='Renewal Notes')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        policy_id = self.env.context.get('default_policy_id') or res.get('policy_id')
        if policy_id:
            policy = self.env['insurance.policy'].browse(policy_id)
            if policy.exists():
                res['policy_id'] = policy.id
                res['renewal_premium'] = policy.premium
                res['new_sum_insured'] = policy.initial_sum_insured
                start_date = (policy.expiry_date + timedelta(days=1)) if policy.expiry_date else fields.Date.today()
                res['new_start_date'] = start_date
                res['new_expiry_date'] = start_date + timedelta(days=365)
                journal = self.env['account.journal'].search([
                    ('type', 'in', ['bank', 'cash']),
                    ('company_id', '=', policy.company_id.id),
                ], limit=1)
                if journal:
                    res['journal_id'] = journal.id
        return res

    def action_confirm(self):
        self.ensure_one()
        if self.renewal_premium <= 0:
            raise UserError(_("Renewal Premium must be greater than zero."))
        if self.new_sum_insured <= 0:
            raise UserError(_("Sum Insured must be greater than zero."))
        if self.new_expiry_date <= self.new_start_date:
            raise UserError(_("New Expiry Date must be after New Start Date."))
        if not self.journal_id:
            raise UserError(_("Please select a Payment Journal."))

        policy = self.policy_id

        # Check if there is already an active/pending renewal
        pending = policy.renewal_history_ids.filtered(
            lambda r: not r.is_policy_number_updated and (not r.payment_id or r.payment_id.state != 'cancel')
        )
        if pending:
            raise UserError(_(
                "A renewal is already in progress for this policy. "
                "Please complete the pending renewal payment and update the policy number first."
            ))

        # 1. Create Renewal History record with expired policy details
        history = self.env['insurance.policy.renewal.history'].create({
            'policy_id': policy.id,
            'expired_policy_number': policy.policy_number,
            'start_date': policy.start_date,
            'end_date': policy.expiry_date,
            'policy_type': policy.policy_type,
            'insurance_type_id': policy.insurance_type_id.id,
            'description': policy.insurance_type_id.name,
            'renewal_premium': self.renewal_premium,
            'new_start_date': self.new_start_date,
            'new_end_date': self.new_expiry_date,
            'new_sum_insured': self.new_sum_insured,
            'is_policy_number_updated': False,
        })

        # 2. Insurer partner
        partner = False
        if policy.insurance_company_id:
            partner = self.env['res.partner'].search([
                ('name', '=', policy.insurance_company_id.name),
            ], limit=1)
            if not partner:
                partner = self.env['res.partner'].sudo().create({
                    'name': policy.insurance_company_id.name,
                    'is_company': True,
                    'supplier_rank': 1,
                })

        # 3. Create Draft account.payment
        payment_vals = {
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': partner.id if partner else False,
            'amount': self.renewal_premium,
            'currency_id': policy.currency_id.id,
            'journal_id': self.journal_id.id,
            'date': fields.Date.today(),
            'memo': f"Renewal Premium — {policy.policy_number}",
            'company_id': policy.company_id.id,
            'is_insurance_payment': True,
            'is_renewal': True,
            'insurance_policy_id': policy.id,
        }
        payment = self.env['account.payment'].create(payment_vals)

        # Link payment
        history.payment_id = payment.id
        policy.write({
            'payment_ids': [(4, payment.id)],
            'payment_status': 'draft',
        })

        policy.message_post(
            body=_(
                "<b>Policy Renewal Initiated:</b><br/>"
                "• Expired Policy No: <b>%s</b><br/>"
                "• Draft Renewal Payment: <b>%s</b> (₹%s)<br/>"
                "• Policy details moved to <b>Renewal History</b> tab.<br/>"
                "Policy number can be updated once the linked payment is marked as Paid."
            ) % (
                policy.policy_number,
                payment.name or 'Draft Payment',
                f"{payment.amount:,.2f}",
            ),
            subtype_xmlid='mail.mt_note',
        )

        return {'type': 'ir.actions.act_window_close'}
