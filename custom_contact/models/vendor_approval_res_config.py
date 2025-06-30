# -*- coding: utf-8 -*-

from ast import literal_eval
from odoo import api, fields, models, _

class VendorApprovalConfig(models.TransientModel):
    _name = 'vendor.approval.config'
    _description = "Vendor Approval Configuration"
    _rec_name = 'vendor_approval_users'


    vendor_approval_users = fields.Many2many('res.users', 'vendor_approval_users_rel', 'name', 'uid', string='Vendor Approval Users',
                                           ondelete="cascade", domain="[('share', '=', False)]")

    def set_config_values(self):
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('vendor.approval.config', 'vendor_approval_users', self.vendor_approval_users.ids)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }