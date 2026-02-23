# -*- coding: utf-8 -*-

import logging
from datetime import datetime

from dateutil.relativedelta import relativedelta
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class KsResUsersInherit(models.Model):
    _inherit = "res.users"

    ks_profile_line_ids = fields.Many2many("user.profiles", "user_profiles_users_rel", 'profile_id', 'user_id',
                                           string="Profile")
    ks_profile_ids = fields.One2many(comodel_name="user.profiles",
                                     string="Profiles",
                                     compute="_compute_profile_ids",
                                     compute_sudo=True,
                                     )
    ks_is_passwd_expired = fields.Boolean('Password Expired', readonly=True)

    ks_user_management_id = fields.Many2many('user.management', 'user_management_users_rel', 'user_id',
                                             'user_management_id', 'Access Pack')
    ks_password_update = fields.Datetime('Password last update time', default=datetime.now())
    ks_password_expire_date = fields.Date(string='Password expire date')
    ks_recent_activity_line = fields.One2many('recent.activity', 'ks_user_id', string='Recent Activity', readonly=True)
    ks_admin_user = fields.Boolean(compute='compute_is_admin_user', string='Admin User', store=True)

    @api.depends('groups_id', 'ks_admin_user')
    def compute_is_admin_user(self):
        """ Compute that the user is admin or not."""
        for rec in self:
            if self.env.ref('base.group_system').id in rec.groups_id.ids:
                rec.ks_admin_user = True
                if rec.ks_profile_line_ids:
                    rec.sudo().write({'ks_profile_line_ids': self.env['user.profiles']})
            else:
                rec.ks_admin_user = False

    def _check_credentials(self, credential, env):
        """ DO force login to any user : Allowed only for admin's """
        try:
            return super(KsResUsersInherit, self)._check_credentials(credential, env)
        except AccessDenied:
            if isinstance(credential, dict) and credential.get('force_login'):
                return {
                    'uid': self.env.user.id,
                    'auth_method': 'password',
                    'mfa': 'default',
                }
            else:
                raise AccessDenied()

    def ks_action_login_confirm(self):
        request.session.authenticate(request.session.db,
                                     {'login': self.login, 'password': self.password,
                                      'force_login': True, 'type': 'password'})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model_create_multi
    def create(self, vals_list):
        """ On creating new user, update the password expiry month if have"""
        new_records = super(KsResUsersInherit, self).create(vals_list)
        for user in new_records:
            if user.ks_profile_line_ids:
                user.sudo().ks_update_group_to_user()
            expire_days = request.env['ir.config_parameter'].sudo().get_param(
                'ks_access_manager_ninja.password_expire_in_days')
            if expire_days:
                user.sudo().ks_password_expire_date = datetime.now() + relativedelta(
                    days=int(expire_days))
        return new_records

    def write(self, vals):
        profile_management = self.env['user.management'].sudo().search(
            [('ks_profile_ids', 'in', self.ks_profile_line_ids.ids)])
        for rec in self:
            if not vals.get('notification_type'):
                notification_type = rec.notification_type
            else:
                notification_type = False
            if notification_type and rec.notification_type != notification_type:
                rec.groups_id = [(4, rec.env.ref('mail.group_mail_notification_type_inbox').id)]
            profile_management.ks_compute_profile_ids()
        res = super(KsResUsersInherit, self).write(vals)
        if vals.get('password'):
            self.sudo().write({'ks_password_update': datetime.now()})
        if vals.get('ks_profile_line_ids'):
            if not self.has_group('base.group_system'):
                self.sudo().ks_update_group_to_user()
        profile_management = self.env['user.management'].sudo().search(
            [('ks_profile_ids', 'in', self.ks_profile_line_ids.ids)])
        profile_management.sudo().ks_compute_profile_ids()
        return res

    def ks_cron_password_expire(self):
        """ Cron for update password mail and password expiration :- Only for normal user not for admin's"""
        users = self.env['res.users'].sudo().search([('active', '=', True)])
        for user in users:
            try:
                if user.has_group('base.group_system'):
                    continue
                expire_month = user.ks_password_expire_date.month
                todays_month = datetime.now().month

                expire_day = user.ks_password_expire_date.day
                todays_day = datetime.now().day

                # Check for sending mail before seven days of expiration date.
                seven_days_before = datetime.now() + relativedelta(days=7)
                one_day_before = datetime.now() + relativedelta(days=1)
                if seven_days_before.month == expire_month and seven_days_before.day == expire_day:
                    template = self.env.ref('ks_access_manager_ninja.email_template_password_expiration_before_seven')
                    template.send_mail(user.id, force_send=True)
                elif one_day_before.month == expire_month and one_day_before.day == expire_day:
                    template = self.env.ref('ks_access_manager_ninja.email_template_password_expiration_before_one')
                    template.send_mail(user.id, force_send=True)
                if user.ks_password_expire_date and expire_day == todays_day and expire_month == todays_month:
                    user.sudo().write({'ks_is_passwd_expired': True})
                    for activity in self.env['recent.activity'].sudo().search([('ks_user_id', '=', user.id)]):
                        activity.ks_action_logout()
                else:
                    user.sudo().write({'ks_is_passwd_expired': False})
            except:
                continue

    @api.depends("ks_profile_line_ids.ks_profile_id")
    def _compute_profile_ids(self):
        for user in self:
            user.sudo().write({'ks_profile_ids': user.ks_profile_line_ids.mapped("ks_profile_id")})

    def ks_get_enabled_profile(self):
        disabled_profile = self.env['user.profile.lines'].sudo().search([('ks_user_id', '=', self.id)]).filtered(
            lambda rec: rec.ks_is_enabled == False and rec.active == True)
        total_profiles = self.ks_profile_line_ids - disabled_profile.mapped('ks_profile_id')
        if disabled_profile:
            disabled_profile.ks_profile_id.write({'ks_user_ids': [(3, self.id)]}, remove_disabled_user=True)
        return total_profiles

    def ks_update_group_to_user(self, force=False):
        """Set (replace) the groups following the profiles defined on users.
        If no profile is defined on the user, its groups are let untouched unless
        the `force` parameter is `True`.
        """
        profile_groups = {}
        # We obtain all the groups associated to each profiles first, so that
        # it is faster to compare later with each user's groups.
        for profile in self.mapped("ks_profile_line_ids.ks_profile_id"):
            profile_groups[profile] = list(
                set(
                    profile.group_id.ids
                    + profile.implied_ids.ids
                    + profile.trans_implied_ids.ids
                )
            )
        for user in self:
            group_ids = []
            for profile_line in user.ks_get_enabled_profile():
                profile = profile_line.ks_profile_id
                group_ids += profile_groups[profile]
            group_ids = list(set(group_ids))  # Remove duplicates IDs
            groups_to_add = list(set(group_ids) - set(user.groups_id.ids))
            groups_to_remove = list(set(user.groups_id.ids) - set(group_ids))
            to_add = [(4, gr) for gr in groups_to_add]
            to_remove = [(3, gr) for gr in groups_to_remove]
            groups = to_remove + to_add
            if groups:
                vals = {"groups_id": groups}
                super(KsResUsersInherit, user).sudo().write(vals)
        return True

    def ks_action_create_profile(self):
        """Open user profile wizard"""
        context = {'default_ks_user_ids': self.ids}
        return {
            'name': _('Create Profile'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'user.profiles',
            'views': [(self.env.ref('ks_access_manager_ninja.view_res_user_profiles_form').id, 'form')],
            'view_id': self.env.ref('ks_access_manager_ninja.view_res_user_profiles_form').id,
            'target': 'new',
            'context': context,
        }


class KsChangePasswordWizard(models.TransientModel):
    _inherit = 'change.password.user'

    def change_password_button(self):
        res = super(KsChangePasswordWizard, self).change_password_button()
        vals = {'ks_password_update': datetime.now(), 'ks_is_passwd_expired': False}
        expire_days = request.env['ir.config_parameter'].sudo().get_param(
            'ks_access_manager_ninja.password_expire_in_days')
        if expire_days:
            vals['ks_password_expire_date'] = datetime.now() + relativedelta(
                days=int(expire_days))
        self.user_id.sudo().write(vals)
        return res


class EmailTemplate(models.Model):
    _inherit = 'mail.template'

    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None, email_layout_xmlid=False):
        try:
            return super(EmailTemplate, self).send_mail(res_id, force_send=force_send, raise_exception=raise_exception,
                                                        email_values=email_values,
                                                        email_layout_xmlid=email_layout_xmlid)
        except UserError:
            # Ignore UserError caused by empty recipients list
            pass
