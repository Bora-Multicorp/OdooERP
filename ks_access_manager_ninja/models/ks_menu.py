# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo.http import request
from odoo.osv import expression

from odoo import _
from odoo import api, models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def search(self, domain, offset=0, limit=None, order=None):
        """Hide menu which is selected inside User management only for the selected users"""
        menu_ids = super(IrUiMenu, self).search(domain, offset=offset, limit=limit, order=order)
        current_user = self.env.user
        try:
            company_ids = request.httprequest.cookies.get('cids') or ''
        except RuntimeError:
            # No HTTP request in context (module update, cron, shell, etc.)
            company_ids = ''

        if company_ids:
            if '-' in company_ids:
                cid = company_ids.split('-')
            else:
                cid = company_ids.split(',')
            lst = [int(x) for x in cid]
            ks_hide_menu_ids = self.env['user.management'].sudo().search(
                [('ks_user_ids', 'in', current_user.ids), ('active', '=', True), ('ks_company_ids', 'in', lst)]).mapped(
                'ks_hide_menu_ids')
        else:
            ks_hide_menu_ids = self.env['user.management'].search(
                [('ks_user_ids', 'in', current_user.ids), ('active', '=', True)]).mapped(
                'ks_hide_menu_ids')
        menu_ids = menu_ids - ks_hide_menu_ids
        return menu_ids

    @api.model
    def load_menus(self, debug):
        """ Loads all menu items (all applications and their sub-menus).

        :return: the menu root
        :rtype: dict('children': menu_nodes)
        """
        fields = ['name', 'sequence', 'parent_id', 'action', 'web_icon']
        menu_roots = self.get_user_roots()
        menu_roots_data = menu_roots.read(fields) if menu_roots else []
        menu_root = {
            'id': False,
            'name': 'root',
            'parent_id': [-1, ''],
            'children': [menu['id'] for menu in menu_roots_data],
        }

        all_menus = {'root': menu_root}

        if not menu_roots_data:
            return all_menus

        # menus are loaded fully unlike a regular tree view, cause there are a
        # limited number of items (752 when all 6.1 addons are installed)
        menus_domain = [('id', 'child_of', menu_roots.ids)]
        blacklisted_menu_ids = self._load_menus_blacklist()
        if blacklisted_menu_ids:
            menus_domain = expression.AND([menus_domain, [('id', 'not in', blacklisted_menu_ids)]])
        menus = self.search(menus_domain)
        menu_items = menus.read(fields)
        xmlids = (menu_roots + menus)._get_menuitems_xmlids()

        # add roots at the end of the sequence, so that they will overwrite
        # equivalent menu items from full menu read when put into id:item
        # mapping, resulting in children being correctly set on the roots.
        menu_items.extend(menu_roots_data)

        mi_attachments = self.env['ir.attachment'].sudo().search_read(
            domain=[('res_model', '=', 'ir.ui.menu'),
                    ('res_id', 'in', [menu_item['id'] for menu_item in menu_items if menu_item['id']]),
                    ('res_field', '=', 'web_icon_data')],
            fields=['res_id', 'datas', 'mimetype'])

        mi_attachment_by_res_id = {attachment['res_id']: attachment for attachment in mi_attachments}

        # set children ids and xmlids
        menu_items_map = {menu_item["id"]: menu_item for menu_item in menu_items}
        for menu_item in menu_items:
            menu_item.setdefault('children', [])
            parent = menu_item['parent_id'] and menu_item['parent_id'][0]
            menu_item['xmlid'] = xmlids.get(menu_item['id'], "")
            if parent in menu_items_map:
                menu_items_map[parent].setdefault(
                    'children', []).append(menu_item['id'])
            attachment = mi_attachment_by_res_id.get(menu_item['id'])
            if attachment:
                menu_item['web_icon_data'] = attachment['datas'].decode()
                menu_item['web_icon_data_mimetype'] = attachment['mimetype']
            else:
                menu_item['web_icon_data'] = False
                menu_item['web_icon_data_mimetype'] = False
        all_menus.update(menu_items_map)

        # sort by sequence
        for menu_id in all_menus:
            all_menus[menu_id]['children'].sort(key=lambda id: all_menus[id]['sequence'])

        # recursively set app ids to related children
        def _set_app_id(app_id, menu):
            menu['app_id'] = app_id
            for child_id in menu['children']:
                _set_app_id(app_id, all_menus[child_id])

        for app in menu_roots_data:
            app_id = app['id']
            _set_app_id(app_id, all_menus[app_id])

        # filter out menus not related to an app (+ keep root menu)
        all_menus = {menu['id']: menu for menu in all_menus.values() if menu.get('app_id')}
        all_menus['root'] = menu_root

        return all_menus

class IrActionsActWindow(models.Model):
    _inherit = 'ir.actions.act_window'

    @api.model
    def read(self, fields=None, load='_classic_read'):
        records = super().read(fields=fields, load=load)

        current_user = self.env.user
        try:
            company_ids = request.httprequest.cookies.get('cids') if request.httprequest else ''
        except RuntimeError:
            # No HTTP request in context (module update, cron, shell, etc.)
            company_ids = ''
        if company_ids:
            if '-' in company_ids:
                cid = company_ids.split('-')
            else:
                cid = company_ids.split(',')
            lst = [int(x) for x in cid]
            ks_hide_menu_ids = self.env['user.management'].sudo().search(
                [('ks_user_ids', 'in', current_user.ids),
                 ('active', '=', True),
                 ('ks_company_ids', 'in', lst)]
            ).mapped('ks_hide_menu_ids')
        else:
            ks_hide_menu_ids = self.env['user.management'].sudo().search(
                [('ks_user_ids', 'in', current_user.ids),
                 ('active', '=', True)]
            ).mapped('ks_hide_menu_ids')

        all_hidden_menus = ks_hide_menu_ids
        if ks_hide_menu_ids:
            all_hidden_menus |= self.env['ir.ui.menu'].sudo().search([
                ('id', 'child_of', ks_hide_menu_ids.ids)
            ])

        for rec in records:
            if rec.get('id'):
                menu = self.env['ir.ui.menu'].sudo().search(
                    [('action', '=', f'ir.actions.act_window,{rec["id"]}')],
                    limit=1
                )
                if menu and menu.id in all_hidden_menus.ids:
                    raise AccessError(_("You don't have access to view this page for the selected company."))

        return records