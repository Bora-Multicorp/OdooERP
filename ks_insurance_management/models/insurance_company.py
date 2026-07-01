# -*- coding: utf-8 -*-

from odoo import fields, models


class InsuranceCompany(models.Model):
    _name = 'insurance.company'
    _description = 'Insurance Company'
    _order = 'name'

    name = fields.Char(
        string='Insurance Company Name',
        required=True,
        help='Full legal name of the insurance provider '
             '(e.g. New India Assurance Co. Ltd., United India Insurance Co. Ltd.).',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Leave empty to make this insurer available across all companies.',
    )
    contact_person = fields.Char(
        string='Contact Person',
        help='Name of the primary point of contact at the insurance company '
             '(e.g. relationship manager or servicing officer).',
    )
    phone = fields.Char(
        string='Phone',
        help='Phone number of the insurance company or contact person for claim and policy queries.',
    )
    email = fields.Char(
        string='Email',
        help='Official email address used for sending declaration letters and policy correspondence. '
             'This is auto-populated in declarations when a policy is selected.',
    )
    address = fields.Text(
        string='Address',
        help='Registered or branch office address of the insurance company. '
             'Used in official correspondence.',
    )
    active = fields.Boolean(
        default=True,
        help='Uncheck to archive this insurer. Archived insurers will not appear in policy dropdowns.',
    )
