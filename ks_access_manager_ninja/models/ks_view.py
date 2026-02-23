# -*- coding: utf-8 -*-

from odoo.http import request

from odoo import models


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def _postprocess_tag_label(self, node, name_manager, node_info):
        """Hide label when the field is hidden inside profile management"""
        label_node = super(IrUiView, self)._postprocess_tag_label(node, name_manager, node_info)
        company_lst = [int(x) for x in request.httprequest.cookies.get('cids').split('-')]
        hidden_fields = self.env['field.access'].sudo().search(
            [('ks_model_id.model', '=', self.model),
             ('ks_user_management_id.active', '=', True),
             ('ks_user_management_id.ks_user_ids', 'in', self._uid),
             ('ks_user_management_id.ks_company_ids', 'in', company_lst)
             ])
        for hide_field in hidden_fields:
            for field_id in hide_field.ks_field_id:
                if (node.get('name') == field_id.name) or (
                        node.tag == 'label' and 'for' in node.attrib.keys() and node.attrib['for'] == field_id.name):
                    if hide_field.ks_field_invisible:
                        node_info['invisible'] = True
                        node.set('invisible', '1')
        return label_node
