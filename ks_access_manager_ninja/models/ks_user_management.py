# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.http import request

from odoo import api, fields, models, _


class KsAccessManagement(models.Model):
    _name = 'user.management'
    _description = 'User Access Management'

    color = fields.Integer(string='Color Index')

    def ks_default_profile_ids(self):
        return self.env['user.profiles'].sudo().search([('implied_ids', '=', self.env.ref('base.group_system').id)]).ids

    name = fields.Char(string='Name')
    active = fields.Boolean(string='Active', default=True)
    ks_readonly = fields.Boolean(string="Readonly",
                                 help='Make the whole database readonly for the users added in this profile.')
    ks_hide_chatter = fields.Boolean(string="Hide Chatter", help="Hide all chatter's for the selected user")
    ks_disable_debug_mode = fields.Boolean(string='Disable Developer Mode',
                                           help="Deactivate debug mode for the selected users.")
    ks_user_ids = fields.Many2many('res.users', 'user_management_users_rel', 'user_management_id', 'user_id',
                                   'Users')
    ks_user_rel_ids = fields.Many2many('res.users', 'res_user_store_rel', string='Store user profiles',
                                       compute='ks_compute_profile_ids')
    ks_profile_ids = fields.Many2many('user.profiles', string='Profiles', required=True)
    ks_company_ids = fields.Many2many('res.company', string='Companies', required=True)
    ks_hide_menu_ids = fields.Many2many('ir.ui.menu', string='Menu')
    ks_model_access_line = fields.One2many('model.access', 'ks_user_management_id', string='Model Access')
    ks_hide_field_line = fields.One2many('field.access', 'ks_user_management_id', string='Field Access')
    ks_domain_access_line = fields.One2many('domain.access', 'ks_user_management_id', string='Domain Access')
    ks_button_tab_access_line = fields.One2many('button.tab.access', 'ks_user_management_id', string='Button Access')
    ks_users_count = fields.Integer(string='Users Count', compute='_compute_users_count')
    ks_hide_filters_groups_line = fields.One2many('filter.group.access', 'ks_user_management_id', string='Filter Group')
    ks_ir_model_access = fields.Many2many('ir.model.access', string='Access Rights', readonly=True)
    ks_ir_rule = fields.Many2many('ir.rule', string='Record Rules', readonly=True)
    ks_profile_domain_model_ids = fields.Many2many('ir.model')
    ks_profile_based_menu = fields.Many2many('ir.ui.menu', 'related_menu_for_profiles', 'profile_ids', 'menu_ids',
                                             compute='_compute_profile_based_menu', store=True)
    is_profile = fields.Boolean(string='Profile Exist')
    ks_is_enterprise = fields.Boolean(string='Is Enterprise', compute='compute_is_enterprise')

    @api.depends('ks_is_enterprise')
    def compute_is_enterprise(self):
        web_exist = self.env['ir.module.module'].sudo().search(
            [('name', '=', 'web_enterprise'), ('state', '=', 'installed')])
        if web_exist:
            self.ks_is_enterprise = True
        else:
            self.ks_is_enterprise = False

    @api.onchange('is_profile', 'ks_profile_ids')
    def onchange_is_profile(self):
        """ Onchange that the profile is selected inside profile management."""
        if self.ks_profile_ids:
            self.is_profile = True
        else:
            self.is_profile = False
        self.ks_user_ids = [(6, 0, self.ks_profile_ids.mapped('ks_user_ids').ids)]
        self.ks_user_rel_ids = [(6, 0, self.ks_profile_ids.mapped('ks_user_ids').ids)]
        access_rights = []
        record_rules = []
        model_ids = []
        for profile in self.ks_profile_ids:
            while True:
                access_rights += profile.mapped('implied_ids').model_access.ids
                record_rules += profile.mapped('implied_ids').rule_groups.ids
                model_ids.extend(profile.mapped('implied_ids').model_access.mapped('model_id').ids)
                if profile.implied_ids:
                    profile = profile.implied_ids
                else:
                    break
        record_rules += self.env['res.groups'].sudo().search([('custom', '=', True)]).mapped('rule_groups').ids
        self.ks_ir_model_access = [(6, 0, access_rights)]
        self.ks_ir_rule = [(6, 0, record_rules)]
        self.ks_profile_domain_model_ids = [(6, 0, model_ids)]

    @api.constrains('ks_company_ids')
    def action_restart(self):
        self.env.registry.clear_cache()

    @api.constrains('name')
    def check_name(self):
        """Restrict admin to create rule as same name which is exist"""
        user_management_pool = self.env['user.management'].sudo()
        for rec in self:
            student = user_management_pool.search_count([('name', '=', rec.name), ('id', '!=', rec.id)])
            if student:
                raise UserError('Name must be unique for managements.')

    @api.model_create_multi
    def create(self, vals_list):
        res = super(KsAccessManagement, self).create(vals_list)
        return res

    @api.depends('ks_users_count')
    def _compute_users_count(self):
        """Compute total user which is selected inside selected profiles"""
        for rec in self:
            rec.ks_users_count = len(self.ks_user_ids)

    @api.depends('ks_profile_based_menu', 'ks_profile_ids')
    def _compute_profile_based_menu(self):
        """Compute menu which is for the selected profile"""
        visible_menu_ids = []
        for rec in self.ks_profile_ids:
            last_group = rec.implied_ids
            while True:
                if last_group:
                    visible_menu_ids.extend(last_group.menu_access.ids)
                    last_group = last_group.implied_ids
                else:
                    break
        self.sudo().write({'ks_profile_based_menu': [(6, 0, list(set(visible_menu_ids)))]})

    @api.depends('ks_profile_ids', 'ks_profile_ids.ks_user_ids')
    def ks_compute_profile_ids(self):
        """Compute profiles users and access rights and domain for selected profile model"""
        for rec in self:
            rec.ks_user_ids = [(6, 0, rec.ks_profile_ids.mapped('ks_user_ids').ids)]
            rec.ks_user_rel_ids = [(6, 0, rec.ks_profile_ids.mapped('ks_user_ids').ids)]
            access_rights = []
            record_rules = []
            model_ids = []
            for profile in rec.ks_profile_ids:
                while True:
                    access_rights += profile.mapped('implied_ids').model_access.ids
                    record_rules += profile.mapped('implied_ids').rule_groups.ids
                    model_ids.extend(profile.mapped('implied_ids').model_access.mapped('model_id').ids)
                    if profile.implied_ids:
                        profile = profile.implied_ids
                    else:
                        break
            record_rules += self.env['res.groups'].sudo().search([('custom', '=', True)]).mapped('rule_groups').ids
            rec.ks_ir_model_access = [(6, 0, access_rights)]
            rec.ks_ir_rule = [(6, 0, record_rules)]
            self.ks_profile_domain_model_ids = [(6, 0, model_ids)]

    def write(self, vals):
        res = super(KsAccessManagement, self).write(vals)
        if vals.get('ks_user_ids'):
            for domain in self.ks_domain_access_line:
                users = self.env['res.users'].sudo().search(
                    [('ks_user_management_id', '=', self.id),
                     ('ks_user_management_id.active', '=', True)])
                domain.ks_rule_id.groups.users = [(6, 0, users.ids)]
        return res

    def unlink(self):
        self.ks_domain_access_line.unlink()
        res = super(KsAccessManagement, self).unlink()
        return res

    def ks_activate_rule(self):
        """ Activate User Management Rule."""
        self.active = True
        for domain in self.ks_domain_access_line:
            domain.ks_rule_id.sudo().write({'active': True})

    def ks_deactivate_rule(self):
        """ Deactivate User Management Rule."""
        self.active = False
        for domain in self.ks_domain_access_line:
            domain.ks_rule_id.sudo().write({'active': False})

    def ks_view_profile_users(self):
        """Open users tree view"""
        return {
            'name': _('Profile Users'),
            'type': 'ir.actions.act_window',
            'view_type': 'list',
            'view_mode': 'list',
            'res_model': 'res.users',
            'view_id': self.env.ref('base.view_users_tree').id,
            'target': 'current',
            'domain': [('id', 'in', self.ks_user_ids.ids)],
            'context': {'create': False},

        }

    def ks_view_profile_record_rules(self):
        """ Open record rules tree view"""
        action = self.env["ir.actions.actions"]._for_xml_id("base.action_rule")
        action["domain"] = [("id", "in", self.ks_ir_rule.ids)]
        return action

    def ks_view_profile_access_rights(self):
        """" Open Access rights tree view"""
        action = self.env["ir.actions.actions"]._for_xml_id("base.ir_access_act")
        action["domain"] = [("id", "in", self.ks_ir_model_access.ids)]
        return action

    def ks_search_action_button(self, model):
        """Hide archive/unarchive and export buttons for selected user based on models."""
        hide_element = []
        company_ids = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        model_access_pool = self.env['model.access'].sudo()

        # Define the base domain
        base_domain = [
            ('ks_model_id.model', '=', model),
            ('ks_user_management_id.active', '=', True),
            ('ks_user_management_id.ks_company_ids', 'in', company_ids),
            ('ks_user_management_id.ks_user_ids', 'in', self.env.user.id),
        ]

        # Check if archive/unarchive buttons should be hidden
        archive_domain = base_domain + [('ks_hide_archive_unarchive', '=', True)]
        if model_access_pool.search_count(archive_domain, limit=1):
            hide_element.extend(['archive', 'unarchive'])

        # Check if export button should be hidden
        export_domain = base_domain + [('ks_hide_export', '=', True)]
        if model_access_pool.search_count(export_domain, limit=1):
            hide_element.append('export')

        insert_domain = base_domain + [('ks_insert_in_spreadsheet', '=', True)]
        if model_access_pool.search_count(insert_domain, limit=1):
            hide_element.append("insert")

        return hide_element

    def ks_search_spread_button(self, view_id):
        """Hide spread for selected user based on models."""
        hide_element = []
        if not view_id:
            return hide_element
        company_ids = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        model_access_pool = self.env['model.access'].sudo()

        # Search model using view id
        model_name = self.env['ir.ui.view'].sudo().browse(view_id).model
        # Define the base domain
        base_domain = [
            ('ks_model_id.model', '=', model_name),
            ('ks_user_management_id.active', '=', True),
            ('ks_user_management_id.ks_company_ids', 'in', company_ids),
            ('ks_user_management_id.ks_user_ids', 'in', self.env.user.id),
        ]

        # Check if Insert in Spreadsheet button should be hidden
        spread_domain = base_domain + [('ks_insert_in_spreadsheet', '=', True)]
        if model_access_pool.search_count(spread_domain, limit=1):
            hide_element.append("SpreadsheetCogMenu")

        return hide_element

    def ks_search_hide_upload_button(self, model):
        """Hide Upload for selected user based on models."""
        if not model:
            return False
        try:
            company_ids = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        except:
            company_ids = [self.env.company.id]
        model_access_pool = self.env['model.access'].sudo()

        domain = [
            ('ks_model_id.model', '=', model),
            ('ks_user_management_id.active', '=', True),
            ('ks_user_management_id.ks_company_ids', 'in', company_ids),
            ('ks_user_management_id.ks_user_ids', 'in', self.env.user.id),
            ('ks_hide_upload', '=', True)
        ]

        try:
            if model_access_pool.search_count(domain, limit=1):
                return True
        except:
            return False
        return False

    def copy(self, default=None):
        """ While duplicating profile management, the profile management name save as (copy)"""
        default = dict(default or {},
                       name=_("%s (copy)", self.name))
        return super().copy(default=default)


class ResCompany(models.Model):
    _inherit = 'res.company'

    color = fields.Integer(string='Color Index')
