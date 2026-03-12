# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import AccessError


class InsuranceCategory(models.Model):
    _name = 'insurance.category'
    _description = 'Insurance Category'
    _order = 'name'

    name = fields.Char(string='Category Name', required=True)
    code = fields.Char(string='Code')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Leave empty to share across all companies.',
    )
    is_misc = fields.Boolean(
        string='Miscellaneous',
        help='Policies under this category appear in Miscellaneous Report',
    )
    active = fields.Boolean(default=True)

    def write(self, vals):
        if not self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            raise AccessError("Only Admin can modify Insurance Categories.")
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            raise AccessError("Only Admin can delete Insurance Categories.")
        return super().unlink()


class InsuranceType(models.Model):
    _name = 'insurance.type'
    _description = 'Insurance Type'
    _order = 'name'

    name = fields.Char(string='Insurance Type', required=True)
    category_id = fields.Many2one('insurance.category', string='Category', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Leave empty to share across all companies.',
    )
    marine_applicability = fields.Selection([
        ('exim', 'EXIM'), ('domestic', 'Domestic'),
        ('both', 'Both'), ('russia', 'Russia Only'),
    ], string='Marine Applicability')
    is_marine = fields.Boolean(string='Is Marine Insurance')
    is_fire_burglary = fields.Boolean(string='Is Fire & Burglary')
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')

    def write(self, vals):
        if not self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            raise AccessError("Only Admin can modify Insurance Types.")
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            raise AccessError("Only Admin can delete Insurance Types.")
        return super().unlink()
