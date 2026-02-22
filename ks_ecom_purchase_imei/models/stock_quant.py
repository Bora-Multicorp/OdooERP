# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def _get_imei_on_hold_location(self):
        """Get the configured On Hold location."""
        ICPSudo = self.env['ir.config_parameter'].sudo()
        location_id = ICPSudo.get_param('ks_ecom_purchase_imei.imei_on_hold_location_id', default=False)
        
        if location_id:
            try:
                return self.env['stock.location'].browse(int(location_id))
            except (ValueError, TypeError):
                pass
        
        return self.env.ref('ks_ecom_purchase_imei.imei_on_hold_location', raise_if_not_found=False)
