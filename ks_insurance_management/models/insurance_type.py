# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import AccessError


class InsuranceCategory(models.Model):
    _name = 'insurance.category'
    _description = 'Insurance Category'
    _order = 'name'

    name = fields.Char(
        string='Category Name',
        required=True,
        help='High-level grouping for insurance policies '
             '(e.g. Fire, Marine, GMC, Vehicle). '
             'Categories are used to filter and organise reports.',
    )
    code = fields.Char(
        string='Code',
        help='Short code for this category used in sequences and reports '
             '(e.g. FIRE, MARINE, GMC).',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Leave empty to make this category available across all companies.',
    )
    is_misc = fields.Boolean(
        string='Miscellaneous',
        help='Mark this category as Miscellaneous. '
             'Policies under miscellaneous categories (e.g. GMC, GPA, Vehicle, Personal) '
             'appear in the Miscellaneous Insurance Report instead of the Fire/Marine reports.',
    )
    active = fields.Boolean(
        default=True,
        help='Uncheck to archive this category. Archived categories will not appear in dropdowns.',
    )

    def write(self, vals):
        if self.env.su or self.env.user.has_group('base.group_system') or self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            return super().write(vals)
        raise AccessError("Only Admin can modify Insurance Categories.")

    def unlink(self):
        if self.env.su or self.env.user.has_group('base.group_system') or self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            return super().unlink()
        raise AccessError("Only Admin can delete Insurance Categories.")


class InsuranceType(models.Model):
    _name = 'insurance.type'
    _description = 'Insurance Type'
    _order = 'name'

    name = fields.Char(
        string='Insurance Type',
        required=True,
        help='Specific type of insurance policy within a category '
             '(e.g. "Marine Open Cover", "Fire Insurance", "Group Mediclaim"). '
             'This is the value users select when creating a policy.',
    )
    category_id = fields.Many2one(
        'insurance.category',
        string='Category',
        required=True,
        help='The parent category this insurance type belongs to. '
             'Determines which report (Marine, Fire & Burglary, or Miscellaneous) '
             'this policy type appears in.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Leave empty to make this type available across all companies.',
    )
    marine_applicability = fields.Selection([
        ('exim', 'EXIM'), ('domestic', 'Domestic'),
        ('both', 'Both'), ('russia', 'Russia Only'),
    ], string='Marine Applicability',
        help='Applicable only when "Is Marine Insurance" is checked. '
             'Defines the geographic scope of the marine cover:\n'
             'EXIM – Export and Import shipments.\n'
             'Domestic – Within-India transit.\n'
             'Both – All shipments (EXIM + Domestic).\n'
             'Russia Only – Specific to Russia trade route.',
    )
    is_marine = fields.Boolean(
        string='Is Marine Insurance',
        help='Check this if policies of this type are Marine insurance. '
             'Marine policies track a running balance sum insured that is '
             'deducted with each sales declaration.',
    )
    is_fire_burglary = fields.Boolean(
        string='Is Fire & Burglary',
        help='Check this if policies of this type are Fire and/or Burglary insurance. '
             'These policies require inventory-value-based periodic declarations.',
    )
    active = fields.Boolean(
        default=True,
        help='Uncheck to archive this type. Archived types will not appear in policy dropdowns.',
    )
    description = fields.Text(
        string='Description',
        help='Detailed description of what this insurance type covers, '
             'special conditions, or notes for the user.',
    )

    def write(self, vals):
        if self.env.su or self.env.user.has_group('base.group_system') or self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            return super().write(vals)
        raise AccessError("Only Admin can modify Insurance Types.")

    def unlink(self):
        if self.env.su or self.env.user.has_group('base.group_system') or self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            return super().unlink()
        raise AccessError("Only Admin can delete Insurance Types.")
