# -*- coding: utf-8 -*-

from odoo import models


class KsBaseModuleUninstall(models.TransientModel):
    _inherit = "base.module.uninstall"

    def action_uninstall(self):
        """ Delete group which is created for user profiles and Domain access"""
        groups = self.env['res.groups']
        category_groups = self.env['res.groups']
        if self.module_id.name == 'ks_access_manager_ninja':
            groups = self.env['res.groups'].sudo().search([('custom', '=', True)])
            category_groups = self.env['res.groups'].sudo().search(
                [('category_id', '=', self.env.ref('ks_access_manager_ninja.ir_module_category_profiles').id)])
        res = super(KsBaseModuleUninstall, self).action_uninstall()
        if groups:
            groups = groups + category_groups
            groups.sudo().unlink()
        return res
