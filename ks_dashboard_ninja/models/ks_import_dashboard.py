# -*- coding: utf-8 -*-

import base64
import logging

from odoo.exceptions import ValidationError

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class KsDashboardNInjaImport(models.TransientModel):
    _name = 'ks_dashboard_ninja.import'
    _description = 'Import Dashboard'

    ks_import_dashboard = fields.Binary(string="Upload Dashboard", attachment=True)
    ks_top_menu_id = fields.Many2one('ir.ui.menu', string="Show Under Menu", domain="[('parent_id','=',False)]",
                                     required=True, default=lambda self: self.env['ir.ui.menu'].search(
                                         [('name', '=', 'My Dashboards')]))


    def create(self, vals):
        """ Save is used in Form View Dialog save callback.
        :param vals:
        :return:
        """
        rec = super().create(vals)
        if 'reload' not in self._context:
            rec.create_dashboard()
        return rec

    def create_dashboard(self):
        try:
            file = base64.b64decode(self.ks_import_dashboard)
            self.env['ks_dashboard_ninja.board'].ks_import_dashboard(file, self.ks_top_menu_id)
            if self._context.get('reload', False):
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
        except Exception as E:
            _logger.warning(E)
            raise ValidationError(_(str(E)))

        return False
