# -*- coding: utf-8 -*-

from odoo import fields, models


class InsuranceAgent(models.Model):
    _name = 'insurance.agent'
    _description = 'Insurance Agent'
    _order = 'name'

    name = fields.Char(
        string='Agent Name',
        required=True,
        help='Full name of the insurance broker or agent who arranged the policy.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Leave empty to make this agent available across all companies.',
    )
    phone = fields.Char(
        string='Phone',
        help='Contact phone number for the agent.',
    )
    email = fields.Char(
        string='Email',
        help='Email address of the agent for policy and renewal communications.',
    )
    license_no = fields.Char(
        string='License Number',
        help='IRDAI (Insurance Regulatory and Development Authority of India) '
             'license number of the insurance agent or broker.',
    )
    insurance_company_id = fields.Many2one(
        'insurance.company',
        string='Insurance Company',
        help='The insurance company this agent is primarily associated with or represents.',
    )
    active = fields.Boolean(
        default=True,
        help='Uncheck to archive this agent. Archived agents will not appear in policy dropdowns.',
    )
    policy_ids = fields.One2many(
        'insurance.policy',
        'agent_id',
        string='Policies',
        help='All insurance policies managed or arranged by this agent.',
    )
    policy_count = fields.Integer(
        compute='_compute_policy_count',
        string='Policy Count',
        help='Total number of active and expired policies linked to this agent.',
    )

    def _compute_policy_count(self):
        for rec in self:
            rec.policy_count = len(rec.policy_ids)
