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

    @api.onchange('move_line_ids', 'move_line_nosuggest_ids')
    def _onchange_move_line_ids_validate_lots_imei(self):
        """Validate lot/serial and IMEI uniqueness across move_line_ids immediately as lines are added/edited in the wizard."""
        for move in self:
            lines = move.move_line_ids | getattr(move, 'move_line_nosuggest_ids', self.env['stock.move.line'])
            if not lines:
                continue

            seen_lots = set()
            seen_imeis = set()
            company_id = move.company_id.id if move.company_id else self.env.company.id
            is_scrap = bool(move.scrapped or move.location_dest_id.scrap_location or move.location_dest_id.usage in ('inventory', 'customer', 'production'))
            is_dest_not_internal = bool(move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal')
            picking_type_code = move.picking_id.picking_type_id.code if move.picking_id else None
            is_outgoing = (picking_type_code == 'outgoing') or is_scrap or is_dest_not_internal

            if is_outgoing or is_scrap:
                continue

            for line in lines:
                lot_str = (line.lot_name or '').strip() or (line.lot_id and line.lot_id.name)
                if lot_str and not is_outgoing:
                    # 1. Stock quant check FIRST (Existing stock item)
                    dq = [('company_id', '=', company_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), ('lot_id.name', '=', lot_str)]
                    if line.lot_id:
                        dq.append(('lot_id', '!=', line.lot_id.id))
                    quant_exist = self.env['stock.quant'].search(dq)
                    if len(quant_exist) > 0:
                        raise ValidationError(_('Serial number (%s) is already used in another stock item.') % lot_str)

                    # 2. In-memory check: duplicate in current wizard lines
                    if lot_str in seen_lots:
                        raise ValidationError(_('Serial number (%s) is already used in another line item in this wizard.') % lot_str)
                    seen_lots.add(lot_str)

                    # 3. Database check: search saved stock.move.line records in DB
                    d = [('company_id', '=', company_id), ('id', '!=', line._origin.id if line._origin else line.id), '|', ('lot_name', '=', lot_str), ('lot_id.name', '=', lot_str)]
                    if move.picking_id:
                        d.append(('picking_id', '=', move.picking_id.id))
                    if line.lot_id:
                        d.append(('lot_id', '!=', line.lot_id.id))
                    exist = self.env['stock.move.line'].search(d, limit=1)
                    if exist and (not line._origin or exist.id != line._origin.id):
                        raise ValidationError(_('Serial number (%s) is already used in another saved line.') % lot_str)

                # IMEI 1 validation
                if line.imei:
                    imei1 = line.imei.strip()
                    if not imei1.isdigit() or len(imei1) != 15:
                        raise ValidationError(_('IMEI 1 must be a 15-digit number. Got: %s') % imei1)
                    if not is_outgoing:
                        # 1. Quant check first
                        d1_q = [('company_id', '=', company_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', imei1), ('imei2', '=', imei1)]
                        if line.lot_id:
                            d1_q.append(('lot_id', '!=', line.lot_id.id))
                        if lot_str:
                            d1_q.append(('lot_id.name', '!=', lot_str))
                        quant_exist = self.env['stock.quant'].search(d1_q)
                        if len(quant_exist) > 0:
                            raise ValidationError(_('IMEI 1 (%s) is already used in stock.') % imei1)

                        # 2. In-memory check
                        if imei1 in seen_imeis:
                            raise ValidationError(_('IMEI 1 (%s) is already used in another line item in this wizard.') % imei1)
                        seen_imeis.add(imei1)

                        # 3. Database line check
                        d1 = [('company_id', '=', company_id), ('id', '!=', line._origin.id if line._origin else line.id), '|', ('imei', '=', imei1), ('imei2', '=', imei1)]
                        if move.picking_id:
                            d1.append(('picking_id', '=', move.picking_id.id))
                        if line.lot_id:
                            d1.append(('lot_id', '!=', line.lot_id.id))
                        if lot_str:
                            d1.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                        exist = self.env['stock.move.line'].search(d1, limit=1)
                        if exist and (not line._origin or exist.id != line._origin.id):
                            raise ValidationError(_('IMEI 1 (%s) is already used in another stock line.') % imei1)

                # IMEI 2 validation
                if move.show_IMEI_field2 and line.imei2:
                    imei2 = line.imei2.strip()
                    if not imei2.isdigit() or len(imei2) != 15:
                        raise ValidationError(_('IMEI 2 must be a 15-digit number. Got: %s') % imei2)
                    if not is_outgoing:
                        # 1. Quant check first
                        d2_q = [('company_id', '=', company_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', imei2), ('imei2', '=', imei2)]
                        if line.lot_id:
                            d2_q.append(('lot_id', '!=', line.lot_id.id))
                        if lot_str:
                            d2_q.append(('lot_id.name', '!=', lot_str))
                        quant_exist = self.env['stock.quant'].search(d2_q)
                        if len(quant_exist) > 0:
                            raise ValidationError(_('IMEI 2 (%s) is already used in stock.') % imei2)

                        # 2. In-memory check
                        if imei2 in seen_imeis:
                            raise ValidationError(_('IMEI 2 (%s) is already used in another line item in this wizard.') % imei2)
                        seen_imeis.add(imei2)

                        # 3. Database line check
                        d2 = [('company_id', '=', company_id), ('id', '!=', line._origin.id if line._origin else line.id), '|', ('imei', '=', imei2), ('imei2', '=', imei2)]
                        if move.picking_id:
                            d2.append(('picking_id', '=', move.picking_id.id))
                        if line.lot_id:
                            d2.append(('lot_id', '!=', line.lot_id.id))
                        if lot_str:
                            d2.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                        exist = self.env['stock.move.line'].search(d2, limit=1)
                        if exist and (not line._origin or exist.id != line._origin.id):
                            raise ValidationError(_('IMEI 2 (%s) is already used in another stock line.') % imei2)

                # IMEI 1 vs IMEI 2 check
                if move.show_IMEI_field2 and line.imei and line.imei2 and line.imei.strip() == line.imei2.strip():
                    product = line.product_id or move.product_id
                    brand_name = (product.product_tmpl_id.brand_id.name or '').lower() if product else ''
                    if brand_name not in ('samsung', 'oneplus'):
                        raise ValidationError(_('IMEI 1 and IMEI 2 must be different.'))


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_in_memory_sibling_move_lines(self):
        """Helper to collect all sibling move lines currently in memory/view context."""
        move_lines = self.env['stock.move.line']
        for record in self:
            if record.move_id:
                move_lines |= record.move_id.move_line_ids
                if hasattr(record.move_id, 'move_line_nosuggest_ids'):
                    move_lines |= record.move_id.move_line_nosuggest_ids
            if record.picking_id:
                move_lines |= record.picking_id.move_line_ids
        return move_lines

    @api.constrains('lot_name')
    def _constrains_validate_lot_name(self):
        for record in self:
            if not record.lot_name:
                continue
            move = record.move_id
            is_scrap = bool(move and (move.scrapped or move.location_dest_id.scrap_location or move.location_dest_id.usage in ('inventory', 'customer', 'production')))
            is_dest_not_internal = bool(move and move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal')
            picking_type_code = move.picking_id.picking_type_id.code if (move and move.picking_id) else None
            is_outgoing = (picking_type_code == 'outgoing') or is_scrap or is_dest_not_internal

            if is_outgoing or is_scrap:
                continue

            company_id = record.company_id.id or (move.company_id.id if move else False) or self.env.company.id
            dq = [
                ('company_id', '=', company_id),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
                ('lot_id.name', '=', record.lot_name)
            ]
            if record.lot_id:
                dq.append(('lot_id', '!=', record.lot_id.id))
            quant = self.env['stock.quant'].search(dq)
            if len(quant) > 0:
                raise ValidationError(
                    _('Serial number (%s) is already used in another stock item.') % record.lot_name)

            if move and move.picking_id:
                d = [
                    ('company_id', '=', company_id),
                    ('picking_id', '=', move.picking_id.id),
                    ('lot_name', '=', record.lot_name),
                    ('id', '!=', record.id)
                ]
                exist = self.search(d, limit=1)
                if exist:
                    raise ValidationError(
                        _('Serial number (%s) is already used in another line of this receipt.') % record.lot_name)

    @api.constrains('imei', 'imei2')
    def _constrains_validate_imei(self):
        for record in self:
            if not record.move_id:
                continue

            move = record.move_id
            is_scrap = bool(move and (move.scrapped or move.location_dest_id.scrap_location or move.location_dest_id.usage in ('inventory', 'customer', 'production')))
            is_dest_not_internal = bool(move and move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal')
            picking_type_code = move.picking_id.picking_type_id.code if (move and move.picking_id) else None
            is_outgoing = (picking_type_code == 'outgoing') or is_scrap or is_dest_not_internal

            if is_outgoing or is_scrap:
                continue

            company_id = record.company_id.id or (move.company_id.id if move else False) or self.env.company.id

            if record.move_id.show_IMEI_field2:
                if record.imei and (not record.imei.isdigit() or len(record.imei) != 15):
                    raise ValidationError(_('IMEI 1 must be a 15-digit number.'))
                if record.imei2 and (not record.imei2.isdigit() or len(record.imei2) != 15):
                    raise ValidationError(_('IMEI 2 must be a 15-digit number.'))
                if record.imei and record.imei2 and record.imei == record.imei2:
                    brand_name = (record.product_id.product_tmpl_id.brand_id.name or '').lower()
                    if brand_name not in ('samsung', 'oneplus'):
                        raise ValidationError(_('IMEI 1 and IMEI 2 must be different.'))
                if not is_outgoing:
                    if record.imei:
                        if move.picking_id:
                            exist = self.search([
                                ('company_id', '=', company_id),
                                ('picking_id', '=', move.picking_id.id),
                                ('imei', '=', record.imei),
                                ('id', '!=', record.id)
                            ], limit=1)
                            if exist:
                                raise ValidationError(_('IMEI 1 (%s) is already used in another line of this receipt.') % record.imei)
                        quant = self.env['stock.quant'].search([
                            ('company_id', '=', company_id),
                            ('quantity', '>', 0),
                            ('location_id.usage', '=', 'internal'),
                            '|', ('imei', '=', record.imei), ('imei2', '=', record.imei)
                        ])
                        if record.lot_id:
                            quant = quant.filtered(lambda q: q.lot_id.id != record.lot_id.id)
                        if quant:
                            raise ValidationError(_('IMEI 1 (%s) is already used in stock.') % record.imei)
                    if record.imei2:
                        if move.picking_id:
                            exist = self.search([
                                ('company_id', '=', company_id),
                                ('picking_id', '=', move.picking_id.id),
                                ('imei2', '=', record.imei2),
                                ('id', '!=', record.id)
                            ], limit=1)
                            if exist:
                                raise ValidationError(_('IMEI 2 (%s) is already used in another line of this receipt.') % record.imei2)
                        quant = self.env['stock.quant'].search([
                            ('company_id', '=', company_id),
                            ('quantity', '>', 0),
                            ('location_id.usage', '=', 'internal'),
                            '|', ('imei', '=', record.imei2), ('imei2', '=', record.imei2)
                        ])
                        if record.lot_id:
                            quant = quant.filtered(lambda q: q.lot_id.id != record.lot_id.id)
                        if quant:
                            raise ValidationError(_('IMEI 2 (%s) is already used in stock.') % record.imei2)

            elif record.move_id.show_IMEI_field:
                if record.imei and (not record.imei.isdigit() or len(record.imei) != 15):
                    raise ValidationError(_('IMEI must be a 15-digit number.'))
                if not is_outgoing and record.imei:
                    if move.picking_id:
                        exist = self.search([
                            ('company_id', '=', company_id),
                            ('picking_id', '=', move.picking_id.id),
                            ('imei', '=', record.imei),
                            ('id', '!=', record.id)
                        ], limit=1)
                        if exist:
                            raise ValidationError(_('IMEI (%s) is already used in another line of this receipt.') % record.imei)
                    quant = self.env['stock.quant'].search([
                        ('company_id', '=', company_id),
                        ('quantity', '>', 0),
                        ('location_id.usage', '=', 'internal'),
                        '|', ('imei', '=', record.imei), ('imei2', '=', record.imei)
                    ])
                    if record.lot_id:
                        quant = quant.filtered(lambda q: q.lot_id.id != record.lot_id.id)
                    if quant:
                        raise ValidationError(_('IMEI (%s) is already used in stock.') % record.imei)
    @api.onchange('imei', 'imei2')
    def _onchange_validate_imei(self):
        warning_msgs = []

        move = self.move_id
        is_scrap = bool(move and (move.scrapped or move.location_dest_id.scrap_location or move.location_dest_id.usage in ('inventory', 'customer', 'production')))
        is_dest_not_internal = bool(move and move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal')
        picking_type_code = (
            move.picking_id.picking_type_id.code
            if move and move.picking_id else None
        )
        is_outgoing = (picking_type_code == 'outgoing') or is_scrap or is_dest_not_internal

        if is_outgoing or is_scrap:
            return

        comp_id = self.company_id.id if self.company_id else self.env.company.id
        lot_str = (self.lot_name or '').strip() or (self.lot_id and self.lot_id.name)

        move_lines = self._get_in_memory_sibling_move_lines()

        # IMEI 1 validations
        if self.imei:
            if not self.imei.isdigit() or len(self.imei) != 15:
                warning_msgs.append(_('IMEI 1 must be a 15-digit number.'))
            elif not is_outgoing:
                # In-memory duplicate check
                for line in move_lines:
                    if line == self or (self._origin and (line == self._origin or line._origin == self._origin)):
                        continue
                    if line.imei == self.imei or line.imei2 == self.imei:
                        warning_msgs.append(_('IMEI 1 (%s) is already used in another line item in this receipt.') % self.imei)
                        break

                d1_q = [('company_id', '=', comp_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', self.imei), ('imei2', '=', self.imei)]
                if self.lot_id:
                    d1_q.append(('lot_id', '!=', self.lot_id.id))
                if lot_str:
                    d1_q.append(('lot_id.name', '!=', lot_str))
                quant_exist = self.env['stock.quant'].search(d1_q)
                if len(quant_exist) > 0:
                    warning_msgs.append(_('IMEI 1 (%s) is already used in stock.') % self.imei)

                if move and move.picking_id:
                    d1 = [('company_id', '=', comp_id), ('picking_id', '=', move.picking_id.id), ('id', '!=', self._origin.id if self._origin else self.id), '|', ('imei', '=', self.imei), ('imei2', '=', self.imei)]
                    if self.lot_id:
                        d1.append(('lot_id', '!=', self.lot_id.id))
                    if lot_str:
                        d1.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                    exist = self.search(d1, limit=1)
                    if exist and (not self._origin or exist.id != self._origin.id):
                        warning_msgs.append(_('IMEI 1 (%s) is already used in another stock line.') % self.imei)

        # IMEI 2 validations
        if self.move_id.show_IMEI_field2 and self.imei2:
            if not self.imei2.isdigit() or len(self.imei2) != 15:
                warning_msgs.append(_('IMEI 2 must be a 15-digit number.'))
            elif not is_outgoing:
                # In-memory duplicate check
                for line in move_lines:
                    if line == self or (self._origin and (line == self._origin or line._origin == self._origin)):
                        continue
                    if line.imei == self.imei2 or line.imei2 == self.imei2:
                        warning_msgs.append(_('IMEI 2 (%s) is already used in another line item in this receipt.') % self.imei2)
                        break

                d2_q = [('company_id', '=', comp_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', self.imei2), ('imei2', '=', self.imei2)]
                if self.lot_id:
                    d2_q.append(('lot_id', '!=', self.lot_id.id))
                if lot_str:
                    d2_q.append(('lot_id.name', '!=', lot_str))
                quant_exist = self.env['stock.quant'].search(d2_q)
                if len(quant_exist) > 0:
                    warning_msgs.append(_('IMEI 2 (%s) is already used in stock.') % self.imei2)

                if move and move.picking_id:
                    d2 = [('company_id', '=', comp_id), ('picking_id', '=', move.picking_id.id), ('id', '!=', self._origin.id if self._origin else self.id), '|', ('imei', '=', self.imei2), ('imei2', '=', self.imei2)]
                    if self.lot_id:
                        d2.append(('lot_id', '!=', self.lot_id.id))
                    if lot_str:
                        d2.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                    exist = self.search(d2, limit=1)
                    if exist and (not self._origin or exist.id != self._origin.id):
                        warning_msgs.append(_('IMEI 2 (%s) is already used in another stock line.') % self.imei2)

        # IMEI 1 and IMEI 2 must differ (except Samsung/OnePlus)
        if self.move_id.show_IMEI_field2 and self.imei and self.imei2 and self.imei == self.imei2:
            brand_name = (self.product_id.product_tmpl_id.brand_id.name or '').lower()
            if brand_name not in ('samsung', 'oneplus'):
                warning_msgs.append(_('IMEI 1 and IMEI 2 must be different.'))

        if warning_msgs:
            raise ValidationError('\n'.join(warning_msgs))

    @api.onchange('lot_name', 'lot_id')
    def _onchange_validate_lot_name(self):
        lot_str = (self.lot_name or '').strip() or (self.lot_id and self.lot_id.name)
        if not lot_str:
            return

        move = self.move_id
        is_scrap = bool(move and (move.scrapped or move.location_dest_id.scrap_location or move.location_dest_id.usage in ('inventory', 'customer', 'production')))
        is_dest_not_internal = bool(move and move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal')
        picking_type_code = (
            move.picking_id.picking_type_id.code
            if move and move.picking_id else None
        )
        is_outgoing = (picking_type_code == 'outgoing') or is_scrap or is_dest_not_internal

        if is_outgoing or is_scrap:
            return

        comp_id = self.company_id.id if self.company_id else self.env.company.id

        # 1. Stock quant check FIRST (existing stock item)
        dq = [('company_id', '=', comp_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), ('lot_id.name', '=', lot_str)]
        if self.lot_id:
            dq.append(('lot_id', '!=', self.lot_id.id))
        quant_exist = self.env['stock.quant'].search(dq)
        if len(quant_exist) > 0:
            raise ValidationError(_('Serial number (%s) is already used in another stock item.') % lot_str)

        # 2. In-memory check against other lines in the same wizard / move / picking
        move_lines = self._get_in_memory_sibling_move_lines()
        for line in move_lines:
            if line == self or (self._origin and (line == self._origin or line._origin == self._origin)):
                continue
            line_lot = (line.lot_name or '').strip() or (line.lot_id and line.lot_id.name)
            if line_lot and line_lot == lot_str:
                raise ValidationError(_('Serial number (%s) is already used in another line item in this wizard.') % lot_str)

        # 3. Database check against saved move lines in DB for this picking
        if move and move.picking_id:
            d = [('company_id', '=', comp_id), ('picking_id', '=', move.picking_id.id), ('id', '!=', self._origin.id if self._origin else self.id), '|', ('lot_name', '=', lot_str), ('lot_id.name', '=', lot_str)]
            if self.lot_id:
                d.append(('lot_id', '!=', self.lot_id.id))
            exist = self.search(d, limit=1)
            if exist and (not self._origin or exist.id != self._origin.id):
                raise ValidationError(_('Serial number (%s) is already used in another saved line.') % lot_str)

    def _validate_imei_lot_on_save(self, vals):
        """Called from create/write to block saving invalid IMEI or duplicate serial/lot."""
        if self.env.context.get('skip_imei_lot_validation'):
            return

        record = self[:1] if self else self.browse()
        imei = vals.get('imei') if 'imei' in vals else (record.imei or None)
        imei2 = vals.get('imei2') if 'imei2' in vals else (record.imei2 or None)
        lot_name = vals.get('lot_name') if 'lot_name' in vals else (record.lot_name or None)

        # Fetch current product ID
        product_id = vals.get('product_id') if isinstance(vals.get('product_id'), int) else (
            record.product_id.id if record else False)

        move = record.move_id or (self.env['stock.move'].browse(vals['move_id']) if vals.get('move_id') else False)
        is_scrap = bool(move and (move.scrapped or move.location_dest_id.scrap_location or move.location_dest_id.usage in ('inventory', 'customer', 'production')))
        is_dest_not_internal = bool(move and move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal')

        picking_type_code = None
        if move and move.picking_id:
            picking_type_code = move.picking_id.picking_type_id.code
        is_outgoing = (picking_type_code == 'outgoing') or is_scrap or is_dest_not_internal

        if is_scrap or is_dest_not_internal:
            return

        # Get company ID for company-scoped validation
        company_id = vals.get('company_id') or (record.company_id.id if record else False) or (move.company_id.id if move else False) or self.env.company.id

        # Validate IMEI 1
        if imei:
            if not imei.isdigit() or len(imei) != 15:
                raise ValidationError(_('IMEI 1 must be a 15-digit number. Got: %s') % imei)

            # Check stock existence in current company
            quant = self.env['stock.quant'].search([
                ('company_id', '=', company_id),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
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
                # Incoming/Internal duplicate checks (scoped to current company and picking)
                if move and move.picking_id:
                    exist = self.search([
                        ('company_id', '=', company_id),
                        ('imei', '=', imei),
                        ('id', 'not in', self.ids),
                        ('picking_id', '=', move.picking_id.id)
                    ], limit=1)
                    if exist:
                        raise ValidationError(_('IMEI 1 (%s) is already used in another line of this receipt.') % imei)
                if record.lot_id:
                    quant = quant.filtered(lambda q: q.lot_id.id != record.lot_id.id)
                if len(quant) > 0:
                    raise ValidationError(_('IMEI 1 (%s) is already allocated in stock.') % imei)

        # Validate IMEI 2
        if imei2:
            if not imei2.isdigit() or len(imei2) != 15:
                raise ValidationError(_('IMEI 2 must be a 15-digit number. Got: %s') % imei2)

            # Check stock existence in current company
            quant = self.env['stock.quant'].search([
                ('company_id', '=', company_id),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
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
                # Incoming/Internal duplicate checks (scoped to current company and picking)
                if move and move.picking_id:
                    exist = self.search([
                        ('company_id', '=', company_id),
                        ('imei2', '=', imei2),
                        ('id', 'not in', self.ids),
                        ('picking_id', '=', move.picking_id.id)
                    ], limit=1)
                    if exist:
                        raise ValidationError(_('IMEI 2 (%s) is already used in another line of this receipt.') % imei2)
                if record.lot_id:
                    quant = quant.filtered(lambda q: q.lot_id.id != record.lot_id.id)
                if len(quant) > 0:
                    raise ValidationError(_('IMEI 2 (%s) is already allocated in stock.') % imei2)

        # IMEI 1 and IMEI 2 must differ (except Samsung/OnePlus)
        if imei and imei2 and imei == imei2:
            product = self.env['product.product'].browse(product_id) if product_id else self.env['product.product']
            brand_name = (product.product_tmpl_id.brand_id.name or '').lower() if product else ''
            if brand_name not in ('samsung', 'oneplus'):
                raise ValidationError(_('IMEI 1 and IMEI 2 must be different.'))

        # Validate Serial/Lot number (scoped to current company)
        if lot_name and not is_outgoing:
            quant = self.env['stock.quant'].search([
                ('company_id', '=', company_id),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal'),
                ('lot_id.name', '=', lot_name)
            ])
            if record.lot_id:
                quant = quant.filtered(lambda q: q.lot_id.id != record.lot_id.id)
            if len(quant) > 0:
                raise ValidationError(_('Serial number (%s) is already used in another stock item.') % lot_name)

            if move and move.picking_id:
                exist = self.search([
                    ('company_id', '=', company_id),
                    ('lot_name', '=', lot_name),
                    ('id', 'not in', self.ids),
                    ('picking_id', '=', move.picking_id.id)
                ], limit=1)
                if exist:
                    raise ValidationError(_('Serial number (%s) is already used in another line of this receipt.') % lot_name)

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

            move = record.move_id
            is_scrap = bool(move and (move.scrapped or move.location_dest_id.scrap_location or move.location_dest_id.usage in ('inventory', 'customer', 'production')))
            is_dest_not_internal = bool(move and move.location_id.usage == 'internal' and move.location_dest_id.usage != 'internal')
            picking_type_code = move.picking_id.picking_type_id.code if (move and move.picking_id) else None
            is_outgoing = (picking_type_code == 'outgoing') or is_scrap or is_dest_not_internal

            if is_outgoing or is_scrap:
                continue

            # If both IMEI 1 and IMEI 2 are completely empty (unpopulated/un-synced line), skip mandatory IMEI enforcement
            if not record.imei and not record.imei2:
                continue
            is_dual_mandatory = bool(
                record.move_id.show_IMEI_field2 and getattr(record.move_id, 'is_dual_sim_mandatory', getattr(record.move_id, 'dual_sim_mode', 'on') == 'on')
            )
            if is_dual_mandatory:
                if not record.imei or not record.imei2:
                    raise ValidationError(_('Please enter both IMEI numbers.'))
            elif record.move_id.show_IMEI_field:
                if not record.imei:
                    raise ValidationError(_('Please enter IMEI number.'))

            if is_dual_mandatory:
                if not record.imei.isdigit() or len(record.imei) != 15 or not record.imei2.isdigit() or len(
                        record.imei2) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))
            elif record.move_id.show_IMEI_field:
                if not record.imei.isdigit() or len(record.imei) != 15:
                    raise ValidationError(_('IMEI number must be a 15-digit number.'))
                if record.imei2 and (not record.imei2.isdigit() or len(record.imei2) != 15):
                    raise ValidationError(_('IMEI 2 number must be a 15-digit number.'))

            company_id = record.company_id.id or (move.company_id.id if move else False) or self.env.company.id

            if move and move.picking_id:
                if record.move_id.show_IMEI_field2:
                    d_line1 = [('company_id', '=', company_id), ('picking_id', '=', move.picking_id.id), ('imei', '=', record.imei), ('id', '!=', record.id)]
                    d_line2 = [('company_id', '=', company_id), ('picking_id', '=', move.picking_id.id), ('imei2', '=', record.imei2), ('id', '!=', record.id)]
                    d_line3 = [('company_id', '=', company_id), ('picking_id', '=', move.picking_id.id), ('imei', '=', record.imei2), ('id', '!=', record.id)]
                    d_line4 = [('company_id', '=', company_id), ('picking_id', '=', move.picking_id.id), ('imei2', '=', record.imei), ('id', '!=', record.id)]
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
                            _('IMEI number must be unique, the IMEI number(%s) is already used in another line of this receipt.' % record.imei))
                    exist = self.search(d_line2, limit=1)
                    if exist:
                        raise ValidationError(
                            _('IMEI number must be unique, the IMEI number(%s) is already used in another line of this receipt.' % record.imei2))
                    exist = self.search(d_line3, limit=1)
                    if exist:
                        raise ValidationError(
                            _('IMEI number must be unique, the IMEI number(%s) is already used in another line of this receipt.' % record.imei2))
                    exist = self.search(d_line4, limit=1)
                    if exist:
                        raise ValidationError(
                            _('IMEI number must be unique, the IMEI number(%s) is already used in another line of this receipt.' % record.imei))
                elif record.move_id.show_IMEI_field:
                    d_line = [('company_id', '=', company_id), ('picking_id', '=', move.picking_id.id), ('imei', '=', record.imei), ('id', '!=', record.id)]
                    if record.lot_id:
                        d_line.append(('lot_id', '!=', record.lot_id.id))
                    lot_str = record.lot_name or (record.lot_id and record.lot_id.name)
                    if lot_str:
                        d_line.extend([('lot_name', '!=', lot_str), ('lot_id.name', '!=', lot_str)])
                    exist = self.search(d_line, limit=1)
                    if exist:
                        raise ValidationError(
                            _('IMEI number must be unique, the IMEI number(%s) is already used in another line of this receipt.' % record.imei))

            if record.move_id.show_IMEI_field2:
                brand_record = record.sudo().product_id.product_tmpl_id.brand_id
                brand_name = brand_record.name if brand_record else ''
                is_brand_samsung_or_oneplus = False
                if brand_name and (brand_name.lower() == 'samsung' or brand_name.lower() == 'oneplus'):
                    is_brand_samsung_or_oneplus = True

                if not is_brand_samsung_or_oneplus and (record.imei == record.imei2):
                    raise ValidationError(
                        _('Both IMEI numbers must be different.'))

                d1_q = [('company_id', '=', company_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', record.imei), ('imei2', '=', record.imei)]
                d2_q = [('company_id', '=', company_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', record.imei2), ('imei2', '=', record.imei2)]
                if record.lot_id:
                    d1_q.append(('lot_id', '!=', record.lot_id.id))
                    d2_q.append(('lot_id', '!=', record.lot_id.id))
                lot_str = record.lot_name or (record.lot_id and record.lot_id.name)
                if lot_str:
                    d1_q.append(('lot_id.name', '!=', lot_str))
                    d2_q.append(('lot_id.name', '!=', lot_str))

                quant1 = self.env['stock.quant'].search(d1_q)
                if len(quant1) > 0:
                    raise ValidationError(_('IMEI 1 (%s) is already used in stock.') % record.imei)

                quant2 = self.env['stock.quant'].search(d2_q)
                if len(quant2) > 0:
                    raise ValidationError(_('IMEI 2 (%s) is already used in stock.') % record.imei2)

            elif record.move_id.show_IMEI_field:
                dq = [('company_id', '=', company_id), ('quantity', '>', 0), ('location_id.usage', '=', 'internal'), '|', ('imei', '=', record.imei), ('imei2', '=', record.imei)]
                if record.lot_id:
                    dq.append(('lot_id', '!=', record.lot_id.id))
                lot_str = record.lot_name or (record.lot_id and record.lot_id.name)
                if lot_str:
                    dq.append(('lot_id.name', '!=', lot_str))

                quant = self.env['stock.quant'].search(dq)
                if len(quant) > 0:
                    raise ValidationError(_('IMEI (%s) is already used in stock.') % record.imei)


