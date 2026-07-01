# -*- coding: utf-8 -*-

from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from odoo.http import request

from odoo import api, fields, models, _


class GeneralSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    password_expire_enable = fields.Boolean(string='Enable Password Expiration',
                                            config_parameter='ks_access_manager_ninja.password_expire_enable')

    password_expire_in_days = fields.Integer(string='Password Expire Days',
                                             config_parameter='ks_access_manager_ninja.password_expire_in_days')

    global_tracking_enable = fields.Boolean(string="Global Tracking",
                                            config_parameter='ks_access_manager_ninja.global_tracking_enable')

    @api.constrains('password_expire_in_days')
    def check_password_expire_in_days(self):
        """Restrict to set password expiry month zero"""
        if self.password_expire_enable and self.password_expire_in_days <= 0:
            raise UserError(_('Please provide expiry day greater than zero...'))

    @api.constrains('global_tracking_enable')
    def clear_global_tracking_cache(self):
        request.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        try:
            config_setting = self.env['res.config.settings'].sudo().search([])
            res = super(GeneralSettings, self).create(vals_list)
            all_users = self.env['res.users'].sudo().search([])
            if not res.password_expire_enable:
                res.password_expire_in_days = 0
                for user in all_users:
                    user.sudo().write({'ks_password_expire_date': False, 'ks_is_passwd_expired': False})
            elif config_setting:
                last_record = config_setting[len(config_setting) - 1]
                if last_record.password_expire_in_days != res.password_expire_in_days:
                    for user in all_users:
                        user.sudo().write({'ks_password_update': datetime.now(),
                                           'ks_password_expire_date': datetime.now() + relativedelta(
                                               days=res.password_expire_in_days)})
            else:
                for user in all_users:
                    user.sudo().write({'ks_password_update': datetime.now(),
                                       'ks_password_expire_date': datetime.now() + relativedelta(
                                           days=res.password_expire_in_days)})
        except Exception as e:
            raise UserError(e)
        return res


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def _load_menus_blacklist(self):
        all_menus = super(IrUiMenu, self)._load_menus_blacklist()
        # Hiding menus based on active_direct_sales field
        active_direct_sales = self.env['ir.config_parameter'].sudo().get_param(
            'ks_access_manager_ninja.global_tracking_enable')
        if not active_direct_sales:
            all_menus.append(self.env.ref('ks_access_manager_ninja.menu_global_tracking_first_form').id)
        return all_menus
