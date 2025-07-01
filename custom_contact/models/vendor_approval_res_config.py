# -*- coding: utf-8 -*-
from odoo import api, fields, models


class VendorApprovalConfig(models.TransientModel):
    _name = 'vendor.approval.config'
    _description = "Vendor Approval Configuration"

    vendor_approval_users = fields.Many2many('res.users', 'vendor_approval_users_rel', 'name', 'uid',
                                             string='Vendor Approval Users',
                                             ondelete="cascade")

    @api.model
    def default_get(self, fields):
        """Fetch saved values when form loads."""
        res = super().default_get(fields)
        IrDefault = self.env['ir.default'].sudo()
        res['vendor_approval_users'] = IrDefault.get(
            'vendor.approval.config', 'vendor_approval_users'
        )
        return res

    def set_config_values(self):
        """Save values to ir.default when 'Save' is clicked."""
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set(
            'vendor.approval.config', 'vendor_approval_users',
            self.vendor_approval_users.ids
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
