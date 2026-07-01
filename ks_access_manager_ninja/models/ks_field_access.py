# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo import fields, models, api, _, tools

RELATIONAL_MODELS = ['purchase.order.line', 'account.move.line', 'sale.order.line', 'stock.move.line', 'project.task.work',
                     'event.registration', 'mrp.bom.line']

UNSUPPORTED_TRACKING_TYPES = ['binary', 'html', 'json', 'reference', 'properties']


class KsFieldAccess(models.Model):
    _name = 'field.access'
    _inherit = ['mail.thread']
    _description = 'Field Access'

    ks_model_id = fields.Many2one('ir.model', string='Model', domain="[('id', 'in', ks_profile_domain_model_ids )]")
    ks_field_id = fields.Many2many('ir.model.fields',
                                   string='Field')
    ks_field_invisible = fields.Boolean(string='Invisible')
    ks_field_readonly = fields.Boolean(string='Readonly')
    ks_field_required = fields.Boolean(string='Required')
    ks_field_external_link = fields.Boolean(string='Remove External Link')
    ks_user_management_id = fields.Many2one('user.management', string='Management')
    ks_profile_domain_model_ids = fields.Many2many('ir.model',
                                                   related='ks_user_management_id.ks_profile_domain_model_ids')
    ks_company_ids = fields.Many2many('res.company', related='ks_user_management_id.ks_company_ids')

    ks_tracking = fields.Boolean(string="Tracking")

    @api.constrains('ks_field_required', 'ks_field_readonly', 'ks_tracking', 'ks_field_id')
    def ks_check_field_access(self):
        for rec in self:
            if rec.ks_field_required and rec.ks_field_readonly:
                raise UserError(_('You can not set field as Readonly and Required at same time.'))
            elif rec.ks_field_required and rec.ks_field_invisible:
                raise UserError(_('You can not set field as Invisible and Required at same time.'))
            for field in rec.ks_field_id:
                if rec.ks_field_required:
                    if self.search([('ks_field_invisible', '=', True), ('ks_field_id', 'in', field.id), (
                            'ks_user_management_id.ks_user_ids', 'in', self.ks_user_management_id.ks_user_ids.ids)]):
                        raise UserError(_('You can not set field as Invisible and Required at same time.'))
                    elif self.search([('ks_field_readonly', '=', True), ('ks_field_id', 'in', field.id), (
                            'ks_user_management_id.ks_user_ids', 'in', self.ks_user_management_id.ks_user_ids.ids)]):
                        raise UserError(_('You can not set field as Readonly and Required at same time.'))
                elif rec.ks_field_invisible:
                    if self.search([('ks_field_required', '=', True), ('ks_field_id', 'in', field.id), (
                            'ks_user_management_id.ks_user_ids', 'in', self.ks_user_management_id.ks_user_ids.ids)]):
                        raise UserError(_('You can not set field as Invisible and Required at same time.'))
                elif rec.ks_field_readonly:
                    if self.search([('ks_field_required', '=', True), ('ks_field_id', 'in', field.id), (
                            'ks_user_management_id.ks_user_ids', 'in', self.ks_user_management_id.ks_user_ids.ids)]):
                        raise UserError(_('You can not set field as Readonly and Required at same time.'))
            
            if rec.ks_tracking:
                unsupported_fields = []
                field_type_names = {
                    'binary': 'Binary',
                    'html': 'HTML',
                    'json': 'JSON',
                    'reference': 'Reference',
                    'properties': 'Properties'
                }
                for field in rec.ks_field_id:
                    if field.ttype in UNSUPPORTED_TRACKING_TYPES:
                        field_type_name = field_type_names.get(field.ttype, field.ttype.title())
                        unsupported_fields.append(f"{field.field_description} ({field_type_name})")
                if unsupported_fields:
                    fields_list = '\n'.join(f"- {f}" for f in unsupported_fields)
                    raise ValidationError(_('You cannot set Tracking for the following fields:\n%s') % fields_list)
                if rec.ks_model_id.model in RELATIONAL_MODELS:
                    raise ValidationError(_('You cannot set Tracking for relational Models.'))

    @api.constrains('ks_field_id', 'ks_tracking', 'ks_company_ids', 'ks_user_management_id.ks_company_ids')
    def action_restart(self):
        self.env.registry.clear_cache()

    def get_track_fields(self):
        model_fields = []
        if self.ks_tracking == True:
            for field_id in self.ks_field_id:
                model_fields.append(field_id.name)
        return model_fields


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @tools.ormcache('self.env.uid', 'self.env.su')
    def _track_get_fields(self):
        model_fields = {
            name
            for name, field in self._fields.items()
            if getattr(field, 'tracking', None) or getattr(field, 'track_visibility', None)
        }
        for value in self:
            extra_fields = value.get_track_fields()
            for i in extra_fields:
                model_fields.add(i)
        return model_fields and set(self.fields_get(model_fields, attributes=()))

    def get_track_fields(self):
        model_fields = []
        try:
            c_ids = request.httprequest.cookies.get('cids')
            if c_ids:
                company_lst = [int(x) for x in c_ids.split('-')]
                fields_tracking = self.env['field.access'].sudo().search(
                    [('ks_model_id.model', '=', self._name),
                     ('ks_user_management_id.active', '=', True),
                     ('ks_user_management_id.ks_user_ids', 'in', self._uid),
                     ('ks_user_management_id.ks_company_ids', 'in', company_lst),
                     ('ks_tracking', '=', True)
                     ])
            else:
                fields_tracking = self.env['field.access'].sudo().search(
                    [('ks_model_id.model', '=', self._name),
                     ('ks_user_management_id.active', '=', True),
                     ('ks_user_management_id.ks_user_ids', 'in', self._uid),
                     ('ks_tracking', '=', True)
                     ])

            global_fields_tracking = self.env['global.tracking'].sudo().search(
                [('g_model_id.model', '=', self._name),
                 ])
            for h in fields_tracking:
                field_ids = h.ks_field_id.filtered(lambda field: field.ttype != 'html')
                for field_id in field_ids:
                    model_fields.append(field_id.name)

            for field_id in global_fields_tracking.g_field_ids:
                model_fields.append(field_id.name)
        except:
            return []
        return model_fields
