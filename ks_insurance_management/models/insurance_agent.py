# -*- coding: utf-8 -*-

from odoo import fields, models


class InsuranceAgent(models.Model):
    _name = 'insurance.agent'
    _description = 'Insurance Agent'
    _order = 'name'

    name = fields.Char(string='Agent Name', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Leave empty to share across all companies.',
    )
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    license_no = fields.Char(string='License Number')
    insurance_company_id = fields.Many2one('insurance.company', string='Insurance Company')
    active = fields.Boolean(default=True)
    policy_ids = fields.One2many('insurance.policy', 'agent_id', string='Policies')
    policy_count = fields.Integer(compute='_compute_policy_count', string='Policy Count')

    def _compute_policy_count(self):
        for rec in self:
            rec.policy_count = len(rec.policy_ids)
