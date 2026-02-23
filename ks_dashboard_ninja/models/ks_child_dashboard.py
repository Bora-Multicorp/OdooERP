# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class KsDashboardNinjaBoardItemAction(models.Model):
    _name = 'ks_dashboard_ninja.child_board'
    _description = 'Dashboard Ninja Child Board'

    name = fields.Char()
    ks_dashboard_ninja_id = fields.Many2one("ks_dashboard_ninja.board", string="Select Dashboard")
    ks_gridstack_config = fields.Char('Item Configurations')
    ks_active = fields.Boolean("Is Selected")
    ks_dashboard_menu_name = fields.Char(string="Menu Name", related='ks_dashboard_ninja_id.ks_dashboard_menu_name', store=True)
    board_type = fields.Selection([('default', 'Default'), ('child', 'Child')])
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    ks_computed_group_access = fields.Many2many('res.groups', compute='_compute_ks_computed_group_access', store=True)

    @api.depends('ks_dashboard_ninja_id', 'ks_dashboard_ninja_id.ks_dashboard_group_access')
    def _compute_ks_computed_group_access(self):
        for record in self:
            record.ks_computed_group_access = record.ks_dashboard_ninja_id.ks_dashboard_group_access

    def write(self,vals):
        return super(KsDashboardNinjaBoardItemAction, self).write(vals)


class DNGridStackLayouts(models.Model):
    _name = 'ks_dashboard_ninja.grid_stack_layouts'
    _description = 'Dashboard Ninja GridStack Layouts'

    name = fields.Char(size=35, readonly=True)
    dn_dashboard_id = fields.Many2one("ks_dashboard_ninja.board", string="Select Dashboard", readonly=True)
    grid_stack_config = fields.Json(string="GridStack Config", default={'temp_key': 'temp_value'}, readonly=True)
    is_default = fields.Boolean(string="Is Default", default=False, readonly=True)
    is_main_layout = fields.Boolean(string="Is Main Dashboard Layout", default=False, readonly=True)     # It signifies whether the layout is the main layout for the dashboard


    def unlink(self):
        for rec in self:
            if rec.is_main_layout:
                raise ValidationError(_("Main Layout can't be deleted"))

            if rec.is_default:
                main_layout = rec.dn_dashboard_id.gs_layout_ids.filtered(lambda layout: layout.is_main_layout)
                main_layout.is_default = True

        result = super(DNGridStackLayouts, self).unlink()
        return result

