# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class InsuranceProperty(models.Model):
    _name = 'insurance.property'
    _description = 'Insurance Property'
    _order = 'name'

    name = fields.Char(
        string='Property Name',
        required=True,
        help='Name of the property used for collateral security.'
    )
    address = fields.Text(
        string='Address',
        help='Address or location details of the property.'
    )
    active = fields.Boolean(
        default=True,
        help='Uncheck to archive this property. Archived properties will not appear in dropdowns.'
    )

    def write(self, vals):
        if self.env.su or self.env.user.has_group('base.group_system') or self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            return super().write(vals)
        raise AccessError("Only Admin can modify Insurance Properties.")

    def unlink(self):
        for rec in self:
            policies_count = self.env['insurance.policy'].search_count([('property_ids', 'in', rec.id)])
            if policies_count > 0:
                raise UserError(
                    "You cannot delete property '%s' because it is used as collateral security in %d insurance policy/policies. "
                    "You can archive it instead." % (rec.name, policies_count)
                )
        if self.env.su or self.env.user.has_group('base.group_system') or self.env.user.has_group('ks_insurance_management.group_insurance_admin'):
            return super().unlink()
        raise AccessError("Only Admin can delete Insurance Properties.")
