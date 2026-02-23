# -*- coding: utf-8 -*-

import ast
import logging

from lxml import etree
from odoo.http import request

from odoo import api, models

_logger = logging.getLogger(__name__)


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def get_views(self, views, options=None):
        """If any button is invisible inside """
        view_ref = super(BaseModel, self).get_views(views, options)
        lst = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        if view_ref.get('views'):
            actions_and_reports = []
            hidden_obj = self.env['model.access'].sudo().search(
                [('ks_user_management_id', 'in', self.env.user.ks_user_management_id.ids),
                 ('ks_model_id.model', '=', self._name),
                 ('ks_user_management_id.ks_company_ids', 'in', lst)])
            for access in hidden_obj:
                actions_and_reports += access.mapped('ks_report_action_ids.ks_action_id').ids
                actions_and_reports += access.mapped('ks_server_action_ids.ks_action_id').ids
            if hidden_obj:
                for view in ['form', 'list']:
                    view_obj = view_ref['views'].get(view)
                    if view_obj:
                        toolbar_obj = view_obj.get('toolbar')
                        if toolbar_obj:
                            print_obj = toolbar_obj.get('print')
                            action_obj = toolbar_obj.get('action')
                        for_print, for_action = [], []
                        if toolbar_obj and print_obj:
                            for print in print_obj:
                                if print['id'] in actions_and_reports:
                                    for_print.append(print)
                        if toolbar_obj and action_obj:
                            for action in action_obj:
                                if action['id'] in actions_and_reports:
                                    for_action.append(action)
                        [action_obj.remove(obj) for obj in for_action]
                        [print_obj.remove(obj) for obj in for_print]

        readonly_access_id = self.env['user.management'].sudo().search([
            ('active', '=', True),
            ('ks_user_ids', 'in', self.env.user.id),
            ('ks_readonly', '=', True),
            ('ks_company_ids', 'in', lst)
        ])
        if readonly_access_id:
            for view_type in ['form', 'list']:
                view_obj = view_ref['views'].get(view_type)
                if view_obj and 'toolbar' in view_obj:
                    del view_obj['toolbar']
        return view_ref

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        view_ref = super().get_view(view_id, view_type, **options)
        doc = etree.XML(view_ref['arch'])

        # Hide Buttons
        self.ks_hide_button(doc, view_ref)

        # Field Access
        self.ks_hide_field(doc, view_ref)
        lst = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        # Hide Export All
        if view_type == 'list':
            is_export_hide = self.env['model.access'].sudo().search(
                [('ks_model_id.model', '=', view_ref['model']), ('ks_user_management_id.active', '=', True),
                 ('ks_user_management_id.ks_company_ids', 'in', lst),
                 ('ks_user_management_id.ks_user_ids', 'in', self.env.user.id), ('ks_hide_export', '=', True)], limit=1)
            if is_export_hide:
                for ele in doc.xpath('//list'):
                    ele.set('export_xlsx', '0')
        # Hide Page
        if view_type == 'form':
            self.ks_hide_page(doc)
        # Hide Filter / GroupBy
        if view_type == 'search':
            doc = self.ks_hide_filter_groupby(doc)
        view_ref['arch'] = etree.tostring(doc, encoding='unicode')
        if view_type == 'form':
            # remove external link
            hide_field_access = self.env['field.access'].sudo().search([
                ('ks_user_management_id.ks_user_ids', 'in', self.env.user.id),
                ('ks_user_management_id.active', '=', True),
                ('ks_model_id.model', '=', view_ref['model']), ('ks_field_external_link', '=', True),
                ('ks_user_management_id.ks_company_ids', 'in', lst)])
            if hide_field_access:
                for field in hide_field_access.mapped('ks_field_id'):
                    if field.ttype in ['many2many', 'many2one']:
                        for field_ele in doc.xpath("//field[@name='" + field.name + "']"):
                            options = 'options' in field_ele.attrib.keys() and field_ele.attrib['options'] or "{}"
                            options = ast.literal_eval(options)
                            try:
                                if field_ele.attrib.get('widget'):
                                    del field_ele.attrib['widget']
                            except Exception as e:
                                _logger.error(e)
                            options.update({'no_create': True, 'no_create_edit': True, 'no_open': True})
                            field_ele.attrib.update({'options': str(options)})
                view_ref['arch'] = etree.tostring(doc, encoding='unicode')

            # Hide All Chatter
            if self.env['user.management'].sudo().search(
                    [('active', '=', True), ('ks_user_ids', 'in', self.env.user.id),
                     ('ks_company_ids', 'in', lst), ('ks_hide_chatter', '=', True)], limit=1).id:
                for div in doc.xpath("//chatter"):
                    div.getparent().remove(div)
                view_ref['arch'] = etree.tostring(doc, encoding='unicode')
        if view_type == 'kanban':
            hide_button_ids = self.env['button.tab.access'].sudo().search([
                ('ks_model_id.model', '=', view_ref['model']), ('ks_user_management_id.active', '=', True),
                ('ks_user_management_id.ks_user_ids', 'in', self._uid),
                ('ks_user_management_id.ks_company_ids', 'in', lst)])
            for button in hide_button_ids:
                for btn in button.ks_hide_button_ids:
                    element = doc.xpath(f"//a[@name='{btn.ks_name}']")
                    for ele in element:
                        ele.attrib.update({'class': 'd-none'})
                    element = doc.xpath(f"//button[@name='{btn.ks_name}']")
                    for ele in element:
                        ele.attrib.update({'class': 'd-none'})
                    element = doc.xpath(f"//object[@name='{btn.ks_name}']")
                    for ele in element:
                        ele.attrib.update({'class': 'd-none'})
                for link in button.ks_kanban_button_ids:
                    if link.ks_button_type == 'edit':
                        element = doc.xpath("//a[@type='edit']")
                    elif link.ks_button_type == 'set_cover':
                        element = doc.xpath("//a[@type='set_cover']")
                    elif link.ks_button_type == 'open':
                        element = doc.xpath("//a[@type='open']")
                    else:
                        element = doc.xpath(f"//a[@name='{link.ks_name}']")
                    for ele in element:
                        if (not ele.text.startswith(
                                '\n') and ele.text == link.ks_tab_button_string) or ele.text.startswith('\n'):
                            ele.attrib.update({'class': 'd-none'})
                for link in button.ks_kanban_button_ids:
                    element = doc.xpath(f"//button[@name='{link.ks_name}']")
                    for ele in element:
                        ele.attrib.update({'class': 'd-none'})
            view_ref['arch'] = etree.tostring(doc, encoding='unicode')

        # Make whole system readonly
        readonly_access_id = self.env['user.management'].sudo().search(
            [('active', '=', True), ('ks_user_ids', 'in', self.env.user.id),
             ('ks_readonly', '=', True), ('ks_company_ids', 'in', lst)])
        if readonly_access_id:
            doc.attrib.update({'create': 'false', 'delete': 'false', 'edit': 'false', 'duplicate': 'false'})
            for btn in doc.xpath("//form//button"):
                btn.attrib.update({'invisible': '1'})

            for action in doc.xpath("//form//header/button"):
                action.attrib.update({'invisible': '1'})

            for a in doc.xpath("//form//header//a"):
                a.attrib.update({'class': 'd-none'})

            for print_btn in doc.xpath("//form//button[contains(@name, 'report_')]"):
                print_btn.attrib.update({'invisible': '1'})

            view_ref['arch'] = etree.tostring(doc, encoding='unicode').replace('&amp;quot;', '&quot;')
        else:
            # Change model access like :- Create, Update , Delete etc.
            change_model_access = self.env['model.access'].sudo().search([
                ('ks_user_management_id.ks_user_ids', 'in', self.env.user.id),
                ('ks_user_management_id.active', '=', True),
                ('ks_model_id.model', '=', view_ref['model']), ('ks_user_management_id.ks_company_ids', 'in', lst)])
            if change_model_access:
                delete = 'true'
                edit = 'true'
                create = 'true'
                duplicate = 'true'
                for remove_action_ids in change_model_access:
                    if remove_action_ids.ks_hide_create:
                        create = 'false'
                    if remove_action_ids.ks_hide_edit:
                        edit = 'false'
                    if remove_action_ids.ks_hide_delete:
                        delete = 'false'
                    if remove_action_ids.ks_hide_duplicate:
                        duplicate = 'false'
                    if remove_action_ids.ks_model_readonly:
                        create, delete, edit = 'false', 'false', 'false'
                doc.attrib.update(
                    {'create': create, 'delete': delete, 'edit': edit, 'duplicate': duplicate})
                view_ref['arch'] = etree.tostring(doc, encoding='unicode')
        return view_ref

    def ks_hide_field(self, doc, view_ref):
        company_lst = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        hidden_fields = self.env['field.access'].sudo().search(
            [('ks_model_id.model', '=', self._name),
             ('ks_user_management_id.active', '=', True),
             ('ks_user_management_id.ks_user_ids', 'in', self._uid),
             ('ks_user_management_id.ks_company_ids', 'in', company_lst)
             ])
        for hide_field in hidden_fields:
            for field_id in hide_field.ks_field_id:
                element = doc.xpath(f"//field[@name='{field_id.name}']")
                if element:
                    for ele in element:
                        if hide_field.ks_field_invisible:
                            ele.set('invisible', '1')
                        if hide_field.ks_field_readonly:
                            ele.set('readonly', '1')
                            ele.set('force_save', '1')
                        if hide_field.ks_field_required:
                            ele.set('required', '1')
                element = doc.xpath(f"//label[@for='{field_id.name}']")
                if element:
                    for ele in element:
                        if ele.get('name') == field_id.name or (
                                ele.tag == 'label' and 'for' in ele.attrib.keys() and ele.attrib[
                            'for'] == field_id.name) and hide_field.ks_field_invisible:
                            ele.set('invisible', '1')
        view_ref['arch'] = etree.tostring(doc, encoding='unicode')

    def ks_hide_page(self, doc):
        company_lst = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        hide_tab_ids = self.env['button.tab.access'].sudo().search(
            [('ks_model_id.model', '=', self._name),
             ('ks_user_management_id.active', '=', True),
             ('ks_user_management_id.ks_user_ids', 'in', self._uid),
             ('ks_user_management_id.ks_company_ids', 'in', company_lst)])

        tabs_ids = hide_tab_ids.mapped('ks_hide_tab_ids')
        if tabs_ids:
            for tab in tabs_ids:
                element = doc.xpath(f"//page[@string='{tab.ks_tab_button_string}']")
                if element:
                    for ele in element:
                        if ele.attrib.get('name'):
                            if tab.ks_name == ele.attrib.get('name'):
                                ele.set('invisible', '1')
                                if 'attrs' in ele.attrib.keys() and ele.attrib['attrs']:
                                    del ele.attrib['attrs']
        return None

    def ks_hide_button(self, doc, view_ref):
        """Hide button which is selected inside profile management/button tab access"""
        lst = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        hide_button_ids = self.env['button.tab.access'].sudo().search([
            ('ks_model_id.model', '=', view_ref['model']), ('ks_user_management_id.active', '=', True),
            ('ks_user_management_id.ks_user_ids', 'in', self._uid),
            ('ks_user_management_id.ks_company_ids', 'in', lst)])
        for button in hide_button_ids:
            for btn in button.ks_hide_button_ids:
                element = doc.xpath(f"//a[@name='{btn.ks_name}']")
                for ele in element:
                    ele.attrib.update({'class': 'd-none'})
                element = doc.xpath(f"//button[@name='{btn.ks_name}']")
                for ele in element:
                    ele.attrib.update({'class': 'd-none'})
                element = doc.xpath(f"//object[@name='{btn.ks_name}']")
                for ele in element:
                    ele.attrib.update({'class': 'd-none'})
            for link in button.ks_kanban_button_ids:
                if link.ks_button_type == 'edit':
                    element = doc.xpath("//a[@type='edit']")
                elif link.ks_button_type == 'set_cover':
                    element = doc.xpath("//a[@type='set_cover']")
                else:
                    element = doc.xpath(f"//a[@name='{link.ks_name}']")
                for ele in element:
                    if (not ele.text.startswith(
                            '\n') and ele.text == link.ks_tab_button_string) or ele.text.startswith('\n'):
                        ele.attrib.update({'class': 'd-none'})
            for link in button.ks_kanban_button_ids:
                element = doc.xpath(f"//button[@name='{link.ks_name}']")
                for ele in element:
                    ele.attrib.update({'class': 'd-none'})
        view_ref['arch'] = etree.tostring(doc, encoding='unicode')

    def ks_hide_filter_groupby(self, doc):
        company_lst = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        hide_filter_ids = self.env['filter.group.access'].sudo().search(
            [('ks_model_id.model', '=', self._name),
             ('ks_user_management_id.active', '=', True),
             ('ks_user_management_id.ks_user_ids', 'in', self._uid),
             ('ks_user_management_id.ks_company_ids', 'in',
              company_lst)])
        filter_ids = hide_filter_ids.mapped('ks_hide_filter_ids')
        if filter_ids:
            for filter in filter_ids:
                element = doc.xpath(f"//filter[@string='{filter.ks_filter_group_string}']")
                if element:
                    for ele in element:
                        ele.set('invisible', '1')
                        if 'attrs' in ele.attrib.keys() and ele.attrib['attrs']:
                            del ele.attrib['attrs']
        group_ids = hide_filter_ids.mapped('ks_hide_group_ids')
        if group_ids:
            for group in group_ids:
                element = doc.xpath(f"//filter[@string='{group.ks_filter_group_string}']")
                if element:
                    for ele in element:
                        ele.set('invisible', '1')
                        if 'attrs' in ele.attrib.keys() and ele.attrib['attrs']:
                            del ele.attrib['attrs']
        return doc
