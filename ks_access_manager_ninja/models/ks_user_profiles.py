# -*- coding: utf-8 -*-

import datetime
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class KsResUserProfiles(models.Model):
    _name = "user.profiles"
    _inherits = {"res.groups": "group_id"}
    _description = "User Profiles"

    def default_setting_id(self):
        return self.env.ref('base.group_system')

    color = fields.Integer(string='Color Index')
    group_id = fields.Many2one(
        comodel_name="res.groups",
        required=True,
        ondelete="cascade",
        readonly=True,
        string="Associated group",
    )

    ks_line_ids = fields.One2many(
        comodel_name="user.profile.lines", inverse_name="ks_profile_id", string="Profile lines"
    )
    ks_user_ids = fields.Many2many(
        "res.users", "user_profiles_users_rel", "user_id", "profile_id", string="Apply to users"
    )
    ks_record_rule_ids = fields.Many2many(
        comodel_name="ir.rule",
        compute="_compute_rule_ids",
        string="Record Rules",
        required=False,
    )
    ks_rules_count = fields.Integer(compute="_compute_rule_ids")
    ks_model_access_ids = fields.Many2many(
        comodel_name="ir.model.access",
        compute="_compute_model_access_ids",
        string="Access Rights",
        required=False,
    )
    ks_model_access_count = fields.Integer(compute="_compute_model_access_ids")
    ks_group_category_id = fields.Many2one(
        related="group_id.category_id",
        default=lambda cls: cls.env.ref("ks_access_manager_ninja.ir_module_category_profiles").id,
        string="Associated category",
        help="Associated group's category",
        readonly=False,
    )
    ks_setting_id = fields.Many2one('res.groups', string='Setting ID', default=default_setting_id)

    @api.depends("implied_ids", "implied_ids.model_access")
    def _compute_model_access_ids(self):
        for rec in self:
            rec.ks_model_access_ids = rec.implied_ids.model_access.ids
            rec.ks_model_access_count = len(rec.ks_model_access_ids)

    @api.depends("implied_ids", "implied_ids.rule_groups")
    def _compute_rule_ids(self):
        for rec in self:
            rec.ks_record_rule_ids = rec.implied_ids.rule_groups.ids
            rec.ks_rules_count = len(rec.ks_record_rule_ids)

    @api.model
    def _bypass_rules(self):
        # Run methods as super user to avoid problems by "Administrator/Access Right"
        return self._name == "user.profiles" and self.env.user.has_group(
            "base.group_erp_manager"
        )

    @api.model_create_multi
    def create(self, vals_list):
        model = (self.sudo() if self._bypass_rules() else self).browse()
        new_records = super(KsResUserProfiles, model).create(vals_list)
        new_records.sudo().ks_update_users()
        all_users = new_records.ks_user_ids.ids + new_records.ks_line_ids.filtered(lambda x: x.ks_is_enabled).mapped(
            'ks_user_id').ids
        new_records.sudo().write(
            {'ks_user_ids': [(6, 0, all_users)]},
            remove_disabled_user=True)
        return new_records

    @api.model
    def default_get(self, fields_list):
        """ Set user type/internal group as a default which creating new profile"""
        res = super(KsResUserProfiles, self).default_get(fields_list)
        default_user_id = self.env['ir.model.data']._xmlid_to_res_id('base.group_user', raise_if_not_found=False)
        res['implied_ids'] = [(6, 0, self.env['res.groups'].browse(default_user_id).ids)]
        return res

    def read(self, fields=None, load="_classic_read"):
        recs = self.sudo() if self._bypass_rules() else self
        return super(KsResUserProfiles, recs).read(fields, load)

    def write(self, vals, remove_disabled_user=False):
        if remove_disabled_user:
            res = super(KsResUserProfiles, self).write(vals)
            return res
        recs = self.sudo() if self._bypass_rules() else self
        groups_vals = {}
        for field in recs.group_id._fields:
            if field in vals:
                groups_vals[field] = vals.pop(field)
        if groups_vals:
            recs.group_id.sudo().write(groups_vals)
            if groups_vals.get('color'):
                vals['color'] = groups_vals.get('color')
        old_users = self.ks_user_ids
        res = super(KsResUserProfiles, recs).write(vals)
        profile_manage = self.env['user.management'].sudo().search([('ks_profile_ids', '=', self.id)])
        for profile in profile_manage:
            profile.ks_compute_profile_ids()
        new_users = self.ks_user_ids.ids
        for user in old_users:
            user.ks_update_group_to_user()
            if user.id not in new_users:
                profile_line_exist = self.env['user.profile.lines'].sudo().search(
                    [('ks_user_id', '=', user.id), ('ks_profile_id', '=', self.id)])
                if profile_line_exist:
                    profile_line_exist.unlink()

        recs.ks_update_users()
        for user in old_users:
            if len(user.ks_profile_line_ids) < 1 and not user.groups_id:
                user.write({'groups_id': [(4, self.env.ref('base.group_portal').id)]})
        return res

    def unlink(self):
        """ Delete group which is created with profile"""
        users = self.mapped("ks_user_ids")
        for rec in self:
            rec.group_id.sudo().unlink()
        res = super(KsResUserProfiles, self).unlink()
        users.sudo().ks_update_group_to_user(force=True)
        for user in users:
            if len(user.ks_profile_line_ids) < 1 and not user.has_group('base.group_user'):
                user.write({'groups_id': [(4, self.env.ref('base.group_portal').id)]})
        return res

    def ks_update_users(self):
        """Update all the users concerned by the profiles identified by `ids`."""
        users = self.mapped("ks_user_ids").filtered(lambda rec: rec.ks_admin_user == False)
        users.ks_update_group_to_user()
        return True

    @api.model
    def ks_cron_update_users(self):
        logging.info("Update user profiles")
        self.sudo().search([]).ks_update_users()

    def ks_show_rule_ids(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_rule")
        action["domain"] = [("id", "in", self.ks_record_rule_ids.ids)]
        return action

    def ks_show_model_access_ids(self):
        action = self.env["ir.actions.actions"]._for_xml_id("base.ir_access_act")
        action["domain"] = [("id", "in", self.ks_model_access_ids.ids)]
        return action

    def ks_action_create_user(self):
        context = {'default_ks_profile_line_ids': self.ids}
        return {
            'name': _('Create User'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'res.users',
            'views': [(self.env.ref('base.view_users_form').id, 'form')],
            'view_id': self.env.ref('base.view_users_form').id,
            'target': 'new',
            'context': context,
        }

    def copy(self, default=None):
        """ While duplicating profile, the profile name save as (copy)"""
        default = dict(default or {},
                       name=_("%s (copy)", self.name))
        return super().copy(default=default)


class KsResUsersProfileLine(models.Model):
    _name = "user.profile.lines"
    _description = "Users profile activation deactivation"
    _rec_name = 'ks_profile_id'

    active = fields.Boolean(related="ks_user_id.active")
    ks_profile_id = fields.Many2one(
        comodel_name="user.profiles", required=True, string="Profiles", ondelete="cascade"
    )
    ks_user_id = fields.Many2one(
        "res.users",
        required=True,
        string="User",
        ondelete="cascade",
    )
    ks_date_from = fields.Date("From")
    ks_date_to = fields.Date("To")
    ks_is_enabled = fields.Boolean("Enabled", compute="_compute_is_enabled")
    _sql_constraints = [
        (
            "user_profile_uniq",
            "unique (ks_user_id,ks_profile_id)",
            "profiles can be assigned to a user only once at a time",
        )
    ]

    @api.depends("ks_date_from", "ks_date_to")
    def _compute_is_enabled(self):
        today = datetime.date.today()
        for profile_line in self:
            profile_line.ks_is_enabled = True
            if profile_line.ks_date_from:
                date_from = profile_line.ks_date_from
                if date_from > today:
                    profile_line.ks_is_enabled = False
            if profile_line.ks_date_to:
                date_to = profile_line.ks_date_to
                if today > date_to:
                    profile_line.ks_is_enabled = False

    def unlink(self):
        users = self.mapped("ks_user_id")
        res = super(KsResUsersProfileLine, self).unlink()
        users.ks_update_group_to_user(force=True)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(KsResUsersProfileLine, self).create(vals_list)
        for rec in res:
            if rec.ks_user_id.id not in rec.ks_profile_id.ks_user_ids.ids:
                rec.ks_profile_id.write({'ks_user_ids': [(4, rec.ks_user_id.id)]}, remove_disabled_user=True)
        return res

    def write(self, vals):
        res = super(KsResUsersProfileLine, self).write(vals)
        for rec in self:
            if rec.ks_is_enabled:
                rec.ks_profile_id.ks_user_ids = [(4, rec.ks_user_id.id)]
        return res

    @api.constrains('ks_date_from', 'ks_date_to')
    def _check_date_range(self):
        for record in self:
            if record.ks_date_to and record.ks_date_from and record.ks_date_to < record.ks_date_from:
                raise ValidationError(
                    "The 'To' date cannot be earlier than the 'From' date."
                )