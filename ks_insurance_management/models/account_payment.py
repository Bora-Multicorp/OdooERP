# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_insurance_payment = fields.Boolean(
        string='Insurance Payment',
        help='Marks this payment as an insurance premium payment. '
             'When checked, the Insurance Details tab becomes visible '
             'and the payment is linked to an insurance policy.',
    )
    insurance_policy_id = fields.Many2one(
        'insurance.policy',
        string='Insurance Policy',
        copy=False,
        help='The insurance policy created from or linked to this payment. '
             'Auto-populated after completing the Insurance Details popup.',
    )
    insurance_popup_done = fields.Boolean(
        default=False,
        copy=False,
        help='Internal flag indicating the Insurance Details popup has been completed '
             'and the policy has been created.',
    )
    ins_company_id = fields.Many2one(
        'res.company',
        string='Insured Company',
        help='The company for which this insurance premium is being paid.',
    )
    ins_type_id = fields.Many2one(
        'insurance.type',
        string='Insurance Type',
        help='Type of insurance being paid for (e.g. Marine Open Cover, Fire Insurance).',
    )
    ins_policy_number = fields.Char(
        string='Policy Number',
        help='Policy number as issued by the insurer. Entered manually after receiving the policy document.',
    )
    ins_sum_insured = fields.Float(
        string='Sum Insured',
        help='The maximum insured amount (coverage value) for the policy being created from this payment.',
    )
    ins_sum_insured_words = fields.Char(
        string='Cover Amount (in Words)',
        compute='_compute_ins_words',
        store=True,
        help='Sum Insured converted to English words (Indian format) for use in letters and certificates.',
    )
    ins_agent = fields.Char(
        string='Agent Name',
        help='Name of the insurance agent or broker who arranged the policy. '
             'If the agent does not exist in the system, a new agent record will be created automatically.',
    )
    ins_insurance_company_id = fields.Many2one(
        'insurance.company',
        string='Insurance Company',
        help='The insurer (insurance provider) who issued this policy.',
    )
    ins_expiry_date = fields.Date(
        string='Expiry Date',
        help='Date on which the insurance policy expires. '
             'The system will send a 30-day advance reminder notification automatically.',
    )
    ins_policy_type = fields.Selection([
        ('individual', 'Individual'), ('floater', 'Floater')],
        string='Policy Type',
        help='Individual: covers a single location.\n'
             'Floater: one policy covering multiple warehouse locations.',
    )
    ins_floater_location_ids = fields.Many2many(
        'stock.warehouse',
        string='Covered Locations (Floater)',
        help='Applicable only for Floater policy type. '
             'Select all warehouse locations covered under this single floater policy.',
    )

    @api.depends('ins_sum_insured')
    def _compute_ins_words(self):
        for rec in self:
            try:
                from num2words import num2words
                rec.ins_sum_insured_words = (
                    num2words(int(rec.ins_sum_insured), lang='en_IN').title()
                    + ' Rupees Only') if rec.ins_sum_insured else ''
            except Exception:
                rec.ins_sum_insured_words = ''

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
            }
        }

    def _create_insurance_policy(self):
        self.ensure_one()
        agent_id = False
        if self.ins_agent:
            agent = self.env['insurance.agent'].search(
                [('name', 'ilike', self.ins_agent)], limit=1)
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
            'sum_insured': self.ins_sum_insured,
            'balance_sum_insured': self.ins_sum_insured,
            'premium': self.amount,
            'expiry_date': self.ins_expiry_date,
            'policy_type': self.ins_policy_type or 'individual',
            'floater_location_ids': [(6, 0, self.ins_floater_location_ids.ids)],
            'payment_id': self.id,
            'state': 'active',
        }
        policy = self.env['insurance.policy'].create(policy_vals)
        self.insurance_policy_id = policy.id
        self.insurance_popup_done = True
        return policy
