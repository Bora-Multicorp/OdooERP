# -*- coding: utf-8 -*-

from lxml import etree

from odoo import models, fields, api


class KsFilterGroupAccess(models.Model):
    _name = 'filter.group.access'
    _description = 'Filter Group Acess'

    ks_model_id = fields.Many2one('ir.model', string='Model', domain="[('id', 'in', ks_profile_domain_model_ids )]")
    ks_model_name = fields.Char(string='Model Name', related='ks_model_id.model', readonly=True, store=True)
    ks_hide_filter_ids = fields.Many2many('filter.group.data', string='Hide Filters')
    ks_hide_group_ids = fields.Many2many('filter.group.data', 'group_access_rel', 'access_id', 'data_id',
                                         string='Hide Groups')
    ks_user_management_id = fields.Many2one('user.management', string='Rule')
    ks_profile_domain_model_ids = fields.Many2many('ir.model',
                                                   related='ks_user_management_id.ks_profile_domain_model_ids')

    @api.onchange('ks_model_id')
    def onchange_ks_model_id(self):
        """Create filter and group-by records in a custom model."""
        if self.ks_model_id and self.ks_model_name:
            filter_group_obj = self.env['filter.group.data']
            view_obj = self.env['ir.ui.view']
            for views in view_obj.sudo().search(
                    [('model', '=', self.ks_model_name), ('type', '=', 'search')]):
                res = self.env[self.ks_model_name].sudo().get_view(view_id=views.id, view_type='search')
                doc = etree.XML(res['arch'])
                filters = doc.xpath("//search/filter")
                groups = doc.xpath("//group//filter")
                if filters:
                    for filter in filters:
                        if filter.get('string'):
                            domain = [('ks_filter_group_string', '=', filter.get('string')),
                                      ('ks_model_id', '=', self.ks_model_id.id), ('ks_type', '=', 'filter')]
                            if filter.get('name'):
                                domain += [('ks_filter_group_name', '=', filter.get('name'))]
                            filter_exist = filter_group_obj.sudo().search(domain, limit=1)
                            if not filter_exist:
                                filter_group_obj.create({
                                    'ks_model_id': self.ks_model_id.id,
                                    'ks_filter_group_name': filter.get('name'),
                                    'ks_filter_group_string': filter.get('string'),
                                    'ks_type': 'filter',
                                })
                if groups:
                    for group in groups:
                        group = group.attrib
                        if group.get('string'):
                            domain = [('ks_filter_group_string', '=', group.get('string')),
                                      ('ks_model_id', '=', self.ks_model_id.id), ('ks_type', '=', 'group')]
                            if group.get('name'):
                                domain += [('ks_filter_group_name', '=', group.get('name'))]
                            group_exist = filter_group_obj.sudo().search(domain, limit=1)
                            if not group_exist:
                                filter_group_obj.create({
                                    'ks_model_id': self.ks_model_id.id,
                                    'ks_filter_group_name': group.get('name'),
                                    'ks_filter_group_string': group.get('string'),
                                    'ks_type': 'group',
                                })


class KsFilterGroupData(models.Model):
    _name = 'filter.group.data'
    _description = 'Store Filter / Group Data'
    _rec_name = 'ks_filter_group_string'

    ks_filter_group_name = fields.Char('Name')
    ks_model_id = fields.Many2one('ir.model', string='Model', index=True, ondelete='cascade', required=True)
    ks_model_name = fields.Char(string='Model Name', related='ks_model_id.model', readonly=True, store=True)
    ks_type = fields.Selection([('filter', 'Filter'), ('group', 'Group')], string="Type",
                               required=True)
    ks_filter_group_string = fields.Char('Filter / Group string', required=True)
