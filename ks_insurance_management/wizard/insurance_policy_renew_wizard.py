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
        required=False,
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

        policy = self.policy_id

        if policy.state == 'under_renewal' or policy.has_pending_renewal:
            raise UserError(_(
                "A renewal is already in progress for this policy. "
                "Please update the policy number for the pending renewal first before creating a new renewal."
            ))

        # 1. Create Renewal History record with expired/previous policy details
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

        # 2. Update main policy: new dates, premium, sum insured, set under_renewal stage,
        #    and mark is_paid as False till renewal payment request is paid
        policy.write({
            'start_date': self.new_start_date,
            'expiry_date': self.new_expiry_date,
            'initial_sum_insured': self.new_sum_insured,
            'premium': self.renewal_premium,
            'state': 'under_renewal',
            'is_paid': False,
            'payment_status': 'draft',
        })

        policy.message_post(
            body=_(
                "<b>Policy Renewal Initiated:</b><br/>"
                "• Previous Policy No: <b>%s</b> moved to Renewal History.<br/>"
                "• New Start Date: <b>%s</b> | New Expiry Date: <b>%s</b><br/>"
                "• New Sum Insured: <b>₹%s</b> | Renewal Premium: <b>₹%s</b><br/>"
                "• Policy moved to <b>Under Renewal</b> stage. Premium payment pending.<br/>"
                "Submit payment request for approval to process payment."
            ) % (
                history.expired_policy_number,
                self.new_start_date,
                self.new_expiry_date,
                f"{self.new_sum_insured:,.2f}",
                f"{self.renewal_premium:,.2f}",
            ),
            subtype_xmlid='mail.mt_note',
        )

        return {'type': 'ir.actions.act_window_close'}
