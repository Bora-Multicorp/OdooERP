# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_insurance_payment = fields.Boolean(string='Insurance Payment')
    insurance_policy_id = fields.Many2one(
        'insurance.policy',
        string='Insurance Policy',
        copy=False,
    )
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
    ins_insurance_company_id = fields.Many2one(
        'insurance.company',
        string='Insurance Company',
    )
    ins_expiry_date = fields.Date(string='Expiry Date')
    ins_policy_type = fields.Selection([
        ('individual', 'Individual'), ('floater', 'Floater')], string='Policy Type')
    ins_floater_location_ids = fields.Many2many(
        'stock.warehouse',
        string='Covered Locations (Floater)',
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
