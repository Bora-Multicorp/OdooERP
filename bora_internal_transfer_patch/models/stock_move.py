# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def action_show_details(self):
        """Override to sync inter-company lots/serials before opening detailed operations wizard (burger icon)."""
        for move in self:
            if move.picking_id:
                try:
                    move.picking_id.sudo()._ks_sync_intercompany_lots_between_picking()
                    move.invalidate_recordset(['move_line_ids'])
                    move.picking_id.invalidate_recordset(['move_line_ids', 'move_ids'])
                except Exception:
                    pass
        return super().action_show_details()


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _validate_imei_lot_on_save(self, vals):
        """Called from create/write to block saving invalid IMEI or duplicate serial/lot."""
        if self.env.context.get('skip_imei_lot_validation'):
            return

        record = self[:1] if self else self.browse()
        imei = vals.get('imei') if 'imei' in vals else (record.imei or None)
        imei2 = vals.get('imei2') if 'imei2' in vals else (record.imei2 or None)
        lot_name = vals.get('lot_name') if 'lot_name' in vals else (record.lot_name or None)

        # Get company ID for company-scoped validation
        company_id = vals.get('company_id')
        if not company_id and record:
            company_id = record.company_id.id
        if not company_id:
            company_id = self.env.company.id

        # Fetch current product ID
        product_id = vals.get('product_id') if isinstance(vals.get('product_id'), int) else (
            record.product_id.id if record else False)

        picking_type_code = None
        if record and record.move_id and record.move_id.picking_id:
            picking_type_code = record.move_id.picking_id.picking_type_id.code
        elif vals.get('move_id'):
            move = self.env['stock.move'].browse(vals['move_id'])
            if move.picking_id:
                picking_type_code = move.picking_id.picking_type_id.code
        is_outgoing = picking_type_code == 'outgoing'

        # Validate IMEI 1
        if imei:
            if not imei.isdigit() or len(imei) != 15:
                raise ValidationError(_('IMEI 1 must be a 15-digit number. Got: %s') % imei)

            # Check stock existence in current company
            quant = self.env['stock.quant'].search([
                ('company_id', '=', company_id),
                '|', ('imei', '=', imei), ('imei2', '=', imei)
            ])

            if is_outgoing:
                if not quant:
                    raise ValidationError(_('IMEI 1 (%s) does not exist in stock.') % imei)
                if product_id and any(q.product_id.id != product_id for q in quant):
                    matched_product = quant[0].product_id.display_name
                    raise ValidationError(
                        _('IMEI 1 (%s) is not valid for this product. It belongs to: %s.') % (imei, matched_product))
            else:
                # Incoming/Internal duplicate checks (scoped to current company)
                exist = self.search([('company_id', '=', company_id), ('imei', '=', imei), ('id', 'not in', self.ids)], limit=1)
                if exist:
                    raise ValidationError(_('IMEI 1 (%s) is already used in another stock line.') % imei)
                if len(quant) > 1:
                    raise ValidationError(_('IMEI 1 (%s) is already allocated in stock.') % imei)

        # Validate IMEI 2
        if imei2:
            if not imei2.isdigit() or len(imei2) != 15:
                raise ValidationError(_('IMEI 2 must be a 15-digit number. Got: %s') % imei2)

            # Check stock existence in current company
            quant = self.env['stock.quant'].search([
                ('company_id', '=', company_id),
                '|', ('imei', '=', imei2), ('imei2', '=', imei2)
            ])

            if is_outgoing:
                if not quant:
                    raise ValidationError(_('IMEI 2 (%s) does not exist in stock.') % imei2)
                if product_id and any(q.product_id.id != product_id for q in quant):
                    matched_product = quant[0].product_id.display_name
                    raise ValidationError(
                        _('IMEI 2 (%s) is not valid for this product. It belongs to: %s.') % (imei2, matched_product))
            else:
                # Incoming/Internal duplicate checks (scoped to current company)
                exist = self.search([('company_id', '=', company_id), ('imei2', '=', imei2), ('id', 'not in', self.ids)], limit=1)
                if exist:
                    raise ValidationError(_('IMEI 2 (%s) is already used in another stock line.') % imei2)
                if len(quant) > 1:
                    raise ValidationError(_('IMEI 2 (%s) is already allocated in stock.') % imei2)

        # IMEI 1 and IMEI 2 must differ (except Samsung/OnePlus)
        if imei and imei2 and imei == imei2:
            product = self.env['product.product'].browse(product_id) if product_id else self.env['product.product']
            brand_name = (product.product_tmpl_id.brand_id.name or '').lower() if product else ''
            if brand_name not in ('samsung', 'oneplus'):
                raise ValidationError(_('IMEI 1 and IMEI 2 must be different.'))

        # Validate Serial/Lot number (scoped to current company)
        if lot_name:
            exist = self.search([('company_id', '=', company_id), ('lot_name', '=', lot_name), ('id', 'not in', self.ids)], limit=1)
            if exist:
                raise ValidationError(_('Serial number (%s) is already used in another line.') % lot_name)
            quant = self.env['stock.quant'].search([('company_id', '=', company_id), ('lot_id.name', '=', lot_name)])
            if len(quant) > 0:
                raise ValidationError(_('Serial number (%s) is already registered in stock.') % lot_name)

    @api.depends('lot_id')
    def _compute_imei(self):
        for line in self:
            if line.imei or line.imei2 or self.env.context.get('skip_imei_lot_validation'):
                continue
            picking = line.picking_id or (line.move_id and line.move_id.picking_id)
            if picking and picking.picking_type_id and picking.picking_type_id.code == 'incoming':
                continue
            super(StockMoveLine, line)._compute_imei()

    def create(self, vals_list):
        records_vals = [vals_list] if isinstance(vals_list, dict) else vals_list
        for vals in records_vals:
            self._validate_imei_lot_on_save(vals)
        return super().create(vals_list)

    def write(self, vals):
        if any(f in vals for f in ('imei', 'imei2', 'lot_name')):
            for record in self:
                record._validate_imei_lot_on_save(vals)
        return super().write(vals)

    def validate_imei_and_serial_number(self):
        for record in self:
            qty = getattr(record, 'quantity', 0.0) or getattr(record, 'qty_done', 0.0)
            if qty <= 0:
                continue
            # If both IMEI 1 and IMEI 2 are completely empty (unpopulated/un-synced line), skip mandatory IMEI enforcement
            if not record.imei and not record.imei2:
                continue
            if record.move_id.show_IMEI_field2:
                if not record.imei or not record.imei2:
                    raise ValidationError(_('Please enter both IMEI numbers.'))
            elif record.move_id.show_IMEI_field:
                if not record.imei:
                    raise ValidationError(_('Please enter IMEI number.'))

            if record.move_id.show_IMEI_field2:
                if not record.imei.isdigit() or len(record.imei) != 15 or not record.imei2.isdigit() or len(
                        record.imei2) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))
            elif record.move_id.show_IMEI_field:
                if not record.imei.isdigit() or len(record.imei) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))

            if record.move_id.show_IMEI_field2:
                d_line1 = [('company_id', '=', record.company_id.id), ('imei', '=', record.imei), ('id', '!=', record.id)]
                d_line2 = [('company_id', '=', record.company_id.id), ('imei2', '=', record.imei2), ('id', '!=', record.id)]
                d_line3 = [('company_id', '=', record.company_id.id), ('imei', '=', record.imei2), ('id', '!=', record.id)]
                d_line4 = [('company_id', '=', record.company_id.id), ('imei2', '=', record.imei), ('id', '!=', record.id)]
                if record.lot_id:
                    d_line1.append(('lot_id', '!=', record.lot_id.id))
                    d_line2.append(('lot_id', '!=', record.lot_id.id))
                    d_line3.append(('lot_id', '!=', record.lot_id.id))
                    d_line4.append(('lot_id', '!=', record.lot_id.id))
                lot_str = record.lot_name or (record.lot_id and record.lot_id.name)
                if lot_str:
                    d_line1.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                    d_line2.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                    d_line3.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                    d_line4.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])

                exist = self.search(d_line1, limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
                exist = self.search(d_line2, limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))
                exist = self.search(d_line3, limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei2))
                exist = self.search(d_line4, limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))
            elif record.move_id.show_IMEI_field:
                d_line = [('company_id', '=', record.company_id.id), ('imei', '=', record.imei), ('id', '!=', record.id)]
                if record.lot_id:
                    d_line.append(('lot_id', '!=', record.lot_id.id))
                lot_str = record.lot_name or (record.lot_id and record.lot_id.name)
                if lot_str:
                    d_line.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                exist = self.search(d_line, limit=1)
                if exist:
                    raise ValidationError(
                        _('IMEI number must be unique, the IMEI number(%s) is already used in another stock item.' % record.imei))

            if record.move_id.show_IMEI_field2:
                brand_record = record.product_id.product_tmpl_id.brand_id
                brand_name = brand_record.name if brand_record else ''
                is_brand_samsung_or_oneplus = False
                if brand_name and (brand_name.lower() == 'samsung' or brand_name.lower() == 'oneplus'):
                    is_brand_samsung_or_oneplus = True

                if not is_brand_samsung_or_oneplus and (record.imei == record.imei2):
                    raise ValidationError(
                        _('Both IMEI numbers must be different.'))

                picking_type_code = record.move_id.picking_id.picking_type_id.code if record.move_id and record.move_id.picking_id else None
                is_outgoing = picking_type_code == 'outgoing'

                if not is_outgoing:
                    d1 = [('company_id', '=', record.company_id.id), ('imei', '=', record.imei), ('id', '!=', record.id)]
                    d1_q = [('company_id', '=', record.company_id.id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', record.imei), ('imei2', '=', record.imei)]
                    d2 = [('company_id', '=', record.company_id.id), ('imei2', '=', record.imei2), ('id', '!=', record.id)]
                    d2_q = [('company_id', '=', record.company_id.id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', record.imei2), ('imei2', '=', record.imei2)]
                    if record.lot_id:
                        d1.append(('lot_id', '!=', record.lot_id.id))
                        d1_q.append(('lot_id', '!=', record.lot_id.id))
                        d2.append(('lot_id', '!=', record.lot_id.id))
                        d2_q.append(('lot_id', '!=', record.lot_id.id))
                    lot_str = record.lot_name or (record.lot_id and record.lot_id.name)
                    if lot_str:
                        d1.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                        d1_q.append(('lot_id.name', '!=', lot_str))
                        d2.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                        d2_q.append(('lot_id.name', '!=', lot_str))

                    exist = self.search(d1, limit=1)
                    if exist:
                        raise ValidationError(_('IMEI 1 (%s) is already used in another stock item.') % record.imei)
                    quant = self.env['stock.quant'].search(d1_q)
                    if len(quant) > 0:
                        raise ValidationError(_('IMEI 1 (%s) is already used in stock.') % record.imei)

                    exist = self.search(d2, limit=1)
                    if exist:
                        raise ValidationError(_('IMEI 2 (%s) is already used in another stock item.') % record.imei2)
                    quant = self.env['stock.quant'].search(d2_q)
                    if len(quant) > 0:
                        raise ValidationError(_('IMEI 2 (%s) is already used in stock.') % record.imei2)

            elif record.move_id.show_IMEI_field:
                picking_type_code = record.move_id.picking_id.picking_type_id.code if record.move_id and record.move_id.picking_id else None
                is_outgoing = picking_type_code == 'outgoing'
                if record.imei and (not record.imei.isdigit() or len(record.imei) != 15):
                    raise ValidationError(_('IMEI must be a 15-digit number.'))
                if not is_outgoing and record.imei:
                    d = [('company_id', '=', record.company_id.id), ('imei', '=', record.imei), ('id', '!=', record.id)]
                    dq = [('company_id', '=', record.company_id.id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', record.imei), ('imei2', '=', record.imei)]
                    if record.lot_id:
                        d.append(('lot_id', '!=', record.lot_id.id))
                        dq.append(('lot_id', '!=', record.lot_id.id))
                    lot_str = record.lot_name or (record.lot_id and record.lot_id.name)
                    if lot_str:
                        d.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                        dq.append(('lot_id.name', '!=', lot_str))
                    exist = self.search(d, limit=1)
                    if exist:
                        raise ValidationError(_('IMEI (%s) is already used in another stock item.') % record.imei)
                    quant = self.env['stock.quant'].search(dq)
                    if len(quant) > 0:
                        raise ValidationError(_('IMEI (%s) is already used in stock.') % record.imei)

    @api.constrains('lot_name')
    def _constrains_validate_lot_name(self):
        for record in self:
            if not record.lot_name:
                continue
            d = [('company_id', '=', record.company_id.id), ('lot_name', '=', record.lot_name), ('id', '!=', record.id)]
            dq = [('company_id', '=', record.company_id.id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), ('lot_id.name', '=', record.lot_name)]
            if record.lot_id:
                d.append(('lot_id', '!=', record.lot_id.id))
                dq.append(('lot_id', '!=', record.lot_id.id))
            exist = self.search(d, limit=1)
            if exist:
                raise ValidationError(
                    _('Serial number (%s) is already used in another line.') % record.lot_name)
            quant = self.env['stock.quant'].search(dq)
            if len(quant) > 0:
                raise ValidationError(
                    _('Serial number (%s) is already used in another stock item.') % record.lot_name)

    @api.onchange('imei', 'imei2')
    def _onchange_validate_imei(self):
        warning_msgs = []

        picking_type_code = (
            self.move_id.picking_id.picking_type_id.code
            if self.move_id and self.move_id.picking_id else None
        )
        is_outgoing = picking_type_code == 'outgoing'

        comp_id = self.company_id.id if self.company_id else self.env.company.id
        lot_str = self.lot_name or (self.lot_id and self.lot_id.name)

        # IMEI 1 validations
        if self.imei:
            if not self.imei.isdigit() or len(self.imei) != 15:
                warning_msgs.append(_('IMEI 1 must be a 15-digit number.'))
            elif not is_outgoing:
                d1 = [('company_id', '=', comp_id), ('imei', '=', self.imei), ('id', '!=', self._origin.id)]
                d1_q = [('company_id', '=', comp_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', self.imei), ('imei2', '=', self.imei)]
                if self.lot_id:
                    d1.append(('lot_id', '!=', self.lot_id.id))
                    d1_q.append(('lot_id', '!=', self.lot_id.id))
                if lot_str:
                    d1.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                    d1_q.append(('lot_id.name', '!=', lot_str))
                exist = self.search(d1, limit=1)
                if exist:
                    warning_msgs.append(_('IMEI 1 (%s) is already used in another stock item.') % self.imei)
                quant_exist = self.env['stock.quant'].search(d1_q)
                if len(quant_exist) > 0:
                    warning_msgs.append(_('IMEI 1 (%s) is already used in stock.') % self.imei)

        # IMEI 2 validations
        if self.move_id.show_IMEI_field2 and self.imei2:
            if not self.imei2.isdigit() or len(self.imei2) != 15:
                warning_msgs.append(_('IMEI 2 must be a 15-digit number.'))
            elif not is_outgoing:
                d2 = [('company_id', '=', comp_id), ('imei2', '=', self.imei2), ('id', '!=', self._origin.id)]
                d2_q = [('company_id', '=', comp_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', self.imei2), ('imei2', '=', self.imei2)]
                if self.lot_id:
                    d2.append(('lot_id', '!=', self.lot_id.id))
                    d2_q.append(('lot_id', '!=', self.lot_id.id))
                if lot_str:
                    d2.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                    d2_q.append(('lot_id.name', '!=', lot_str))
                exist = self.search(d2, limit=1)
                if exist:
                    warning_msgs.append(_('IMEI 2 (%s) is already used in another stock item.') % self.imei2)
                quant_exist = self.env['stock.quant'].search(d2_q)
                if len(quant_exist) > 0:
                    warning_msgs.append(_('IMEI 2 (%s) is already used in stock.') % self.imei2)

        # IMEI 1 and IMEI 2 must differ (except Samsung/OnePlus)
        if self.move_id.show_IMEI_field2 and self.imei and self.imei2 and self.imei == self.imei2:
            brand_name = (self.product_id.product_tmpl_id.brand_id.name or '').lower()
            if brand_name not in ('samsung', 'oneplus'):
                warning_msgs.append(_('IMEI 1 and IMEI 2 must be different.'))

        if warning_msgs:
            return {'warning': {'title': _('IMEI Validation'), 'message': '\n'.join(warning_msgs)}}

    @api.onchange('lot_name')
    def _onchange_validate_lot_name(self):
        if not self.lot_name:
            return
        warning_msgs = []

        comp_id = self.company_id.id if self.company_id else self.env.company.id
        d = [('company_id', '=', comp_id), ('lot_name', '=', self.lot_name), ('id', '!=', self._origin.id)]
        dq = [('company_id', '=', comp_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), ('lot_id.name', '=', self.lot_name)]
        if self.lot_id:
            d.append(('lot_id', '!=', self.lot_id.id))
            dq.append(('lot_id', '!=', self.lot_id.id))

        exist = self.search(d, limit=1)
        if exist:
            warning_msgs.append(_('Serial number (%s) is already used in another line.') % self.lot_name)

        quant_exist = self.env['stock.quant'].search(dq)
        if len(quant_exist) > 0:
            warning_msgs.append(_('Serial number (%s) is already used in another stock item.') % self.lot_name)

        if warning_msgs:
            return {'warning': {'title': _('Serial Number Validation'), 'message': '\n'.join(warning_msgs)}}
