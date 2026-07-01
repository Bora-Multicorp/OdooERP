# -*- coding: utf-8 -*-

from odoo import fields, models, api


class KsGlobalTrackingFirst(models.Model):
    _name = 'global.tracking.first'
    _description = 'Global Tracking Fist'
    _inherit = ['mail.thread']

    name = fields.Char(string='Name')
    global_tracking_line = fields.One2many('global.tracking', 'gt_first_id', string='Global Tracking Line')

    @api.constrains('global_tracking_line')
    def action_restart(self):
        self.env.registry.clear_cache()

    def get_track_fields(self):
        model_fields = []
        for hide_field in self.global_tracking_line.mapped('g_field_ids'):
            model_fields.append(hide_field.name)
        return model_fields


class KsGlobalTracking(models.Model):
    _name = 'global.tracking'
    _description = 'Global Tracking'
    _inherit = ['mail.thread']

    g_model_id = fields.Many2one('ir.model', string='Model')
    g_field_ids = fields.Many2many('ir.model.fields', string='Field')
    global_tracking = fields.Boolean(string="Global Tracking")
    profile_tracking = fields.Boolean(string="Profile Tracking")
    profile_ids = fields.Many2many('res.users')
    gt_first_id = fields.Many2one('global.tracking.first')
