# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    imei_on_hold_location_id = fields.Many2one(
        comodel_name='stock.location',
        string="IMEI On Hold Location",
        domain="[('usage', '=', 'internal')]",
        help="Location where products with IMEI mismatches will be placed on hold. "
             "If not set, the default 'IMEI On Hold' location will be used."
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        location_id = ICPSudo.get_param('ks_ecom_purchase_imei.imei_on_hold_location_id', default=False)
        if location_id:
            try:
                res['imei_on_hold_location_id'] = int(location_id)
            except (ValueError, TypeError):
                res['imei_on_hold_location_id'] = False
        else:
            res['imei_on_hold_location_id'] = False
        return res

    def set_values(self):
        super().set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param(
            'ks_ecom_purchase_imei.imei_on_hold_location_id',
            str(self.imei_on_hold_location_id.id) if self.imei_on_hold_location_id else ''
        )
