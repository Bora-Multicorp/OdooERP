# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import ValidationError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.constrains('imei', 'imei2')
    def _check_imei_uniqueness(self):
        for record in self:
            if not record.imei and not record.imei2:
                continue

            # check if tracking is enabled on product template
            tracking = record.product_id.product_tmpl_id.tracking
            is_mobile = getattr(record.product_id.product_tmpl_id, 'is_mobile_category_selected', False) or getattr(record.product_id.product_tmpl_id, 'is_mobile', False)

            # If tracking is enabled (serial/lot), serial number (lot_id) must be present
            if tracking != 'none' and not record.lot_id.id:
                raise ValidationError(_('Please enter serial number.'))

            if not is_mobile or record.location_id.usage not in ('internal', 'transit'):
                continue

            # Ensure IMEIs are not empty
            if record.imei and record.imei2:
                if not record.imei.isdigit() or len(record.imei) != 15:
                    raise ValidationError(
                        f"IMEI number '{record.imei}' must be a 15-digit number for product '{record.product_id.product_tmpl_id.name}'")
                if not record.imei2.isdigit() or len(record.imei2) != 15:
                    raise ValidationError(
                        f"IMEI 2 number '{record.imei2}' must be a 15-digit number for product '{record.product_id.product_tmpl_id.name}'")

                # check if brand is samsung or oneplus, as these two brands have imei1 and imei2 field's same value 
                brand_record = record.product_id.product_tmpl_id.brand_id
                brand_name = brand_record.name if brand_record else ''
                is_brand_samsung_or_oneplus = False
                if brand_name and (brand_name.lower() == 'samsung' or brand_name.lower() == 'oneplus'):
                    is_brand_samsung_or_oneplus = True

                if not is_brand_samsung_or_oneplus and (record.imei == record.imei2):
                    raise ValidationError(
                        f"Both IMEI numbers must be different for product '{record.product_id.product_tmpl_id.name}'")

                domain_imei = [
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id),
                    ('quantity', '>', 0),
                    ('location_id.usage', '=', 'internal'),
                    '|',
                    ('imei', '=', record.imei),
                    ('imei2', '=', record.imei)
                ]
                domain_imei2 = [
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id),
                    ('quantity', '>', 0),
                    ('location_id.usage', '=', 'internal'),
                    '|',
                    ('imei', '=', record.imei2),
                    ('imei2', '=', record.imei2)
                ]
                if record.lot_id:
                    domain_imei.append(('lot_id', '!=', record.lot_id.id))
                    domain_imei2.append(('lot_id', '!=', record.lot_id.id))
                if record.lot_id and record.lot_id.name:
                    domain_imei.append(('lot_id.name', '!=', record.lot_id.name))
                    domain_imei2.append(('lot_id.name', '!=', record.lot_id.name))

                imei_results = self.env['stock.quant'].search(domain_imei)
                imei2_results = self.env['stock.quant'].search(domain_imei2)

                if len(imei_results) > 0:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
                if len(imei2_results) > 0:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))

            else:
                domain_single = [
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id),
                    ('quantity', '>', 0),
                    ('location_id.usage', '=', 'internal'),
                    '|',
                    ('imei', '=', record.imei),
                    ('imei2', '=', record.imei)
                ]
                if record.lot_id:
                    domain_single.append(('lot_id', '!=', record.lot_id.id))
                if record.lot_id and record.lot_id.name:
                    domain_single.append(('lot_id.name', '!=', record.lot_id.name))

                result_items = self.env['stock.quant'].search(domain_single)

                if len(result_items) > 0:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
