# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError


class InsurancePaymentPopupWizard(models.TransientModel):
    _name = 'insurance.payment.popup.wizard'
    _description = 'Insurance Payment Details Popup'

    payment_id = fields.Many2one('account.payment', string='Payment', required=True)
    premium = fields.Float(string='Premium (Incl. GST)')
    company_id = fields.Many2one('res.company', string='Company',
                                  default=lambda self: self.env.company)
    insurance_type_id = fields.Many2one('insurance.type',
                                         string='Insurance Type', required=True)
    policy_number = fields.Char(string='Policy Number')
    sum_insured = fields.Float(string='Sum Insured', required=True)
    sum_insured_words = fields.Char(string='Cover Amount (in Words)',
                                     compute='_compute_words', store=True)
    agent = fields.Char(string='Agent')
    insurance_company_id = fields.Many2one('insurance.company',
                                            string='Insurance Company', required=True)
    expiry_date = fields.Date(string='Expiry Date', required=True)
    policy_type = fields.Selection([
        ('individual', 'Individual'), ('floater', 'Floater')
    ], string='Policy Type', default='individual', required=True)
    floater_location_ids = fields.Many2many('stock.warehouse', string='Covered Locations')

    @api.depends('sum_insured')
    def _compute_words(self):
        for rec in self:
            try:
                from num2words import num2words
                rec.sum_insured_words = (
                    num2words(int(rec.sum_insured), lang='en_IN').title()
                    + ' Rupees Only') if rec.sum_insured else ''
            except Exception:
                rec.sum_insured_words = ''

    @api.onchange('policy_type')
    def _onchange_policy_type(self):
        if self.policy_type == 'individual':
            self.floater_location_ids = [(5,)]

    def action_confirm(self):
        self.ensure_one()
        if self.policy_type == 'floater' and not self.floater_location_ids:
            raise UserError("Please select at least one location for Floater policy.")
        self.payment_id.write({
            'is_insurance_payment': True,
            'ins_company_id': self.company_id.id,
            'ins_type_id': self.insurance_type_id.id,
            'ins_policy_number': self.policy_number,
            'ins_sum_insured': self.sum_insured,
            'ins_agent': self.agent,
            'ins_insurance_company_id': self.insurance_company_id.id,
            'ins_expiry_date': self.expiry_date,
            'ins_policy_type': self.policy_type,
            'ins_floater_location_ids': [(6, 0, self.floater_location_ids.ids)],
        })
        policy = self.payment_id._create_insurance_policy()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Insurance Policy',
            'res_model': 'insurance.policy',
            'res_id': policy.id,
            'view_mode': 'form',
            'target': 'current',
        }
