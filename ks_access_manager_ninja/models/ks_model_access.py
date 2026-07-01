# -*- coding: utf-8 -*-

from odoo import fields, models


class KsRemoveAction(models.Model):
    _name = 'model.access'
    _description = 'Remove Action from model'

    ks_model_id = fields.Many2one('ir.model', string='Model', domain="[('id', 'in', ks_profile_domain_model_ids)]")
    ks_server_action_ids = fields.Many2many('report.action.data', 'server_action_data_rel_ah',
                                            'action_action_id', 'server_action_id', 'Hide Actions',
                                            domain="[('ks_action_id.binding_model_id','=',ks_model_id),('ks_action_id.type','!=','ir.actions.report')]")
    ks_report_action_ids = fields.Many2many('report.action.data', 'remove_action_report_action_data_rel_ah',
                                            'action_action_id', 'report_action_id', 'Hide Reports',
                                            domain="[('ks_action_id.binding_model_id','=',ks_model_id),('ks_action_id.type','=','ir.actions.report')]")

    ks_model_readonly = fields.Boolean('Read-only')
    ks_hide_create = fields.Boolean(string='Hide Create')
    ks_hide_upload = fields.Boolean(string='Hide Upload')
    ks_hide_edit = fields.Boolean(string='Hide Edit')
    ks_hide_delete = fields.Boolean(string='Hide Delete')
    ks_hide_archive_unarchive = fields.Boolean(string='Hide Archive/Unarchive')
    ks_hide_duplicate = fields.Boolean(string='Hide Duplicate')
    ks_hide_export = fields.Boolean(string='Hide Export')
    ks_insert_in_spreadsheet = fields.Boolean(string='Hide Spreadsheet(insert)')
    ks_user_management_id = fields.Many2one('user.management', string='Management Id')
    ks_profile_domain_model_ids = fields.Many2many('ir.model',
                                                   related='ks_user_management_id.ks_profile_domain_model_ids')


class KsRemoveActionData(models.Model):
    _name = 'report.action.data'
    _description = "Store Action Button Data"

    name = fields.Char(string='Name')
    ks_action_id = fields.Many2one('ir.actions.actions', string='Action')
