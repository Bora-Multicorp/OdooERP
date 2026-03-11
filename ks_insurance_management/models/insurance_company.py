# -*- coding: utf-8 -*-

from odoo import fields, models


class InsuranceCompany(models.Model):
    _name = 'insurance.company'
    _description = 'Insurance Company'
    _order = 'name'

    name = fields.Char(string='Insurance Company Name', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Leave empty to share across all companies.',
    )
    contact_person = fields.Char(string='Contact Person')
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email')
    address = fields.Text(string='Address')
    active = fields.Boolean(default=True)
