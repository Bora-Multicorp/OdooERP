# -*- coding: utf-8 -*-

import logging
from odoo import models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        """Override to check stock availability and sync inter-company delivery lots/serials to receipt."""
        try:
            self.sudo()._ks_sync_intercompany_lots_between_picking()
        except Exception as e:
            _logger.warning("Failed to sync inter-company lots on _action_done: %s", str(e), exc_info=True)
        result = super()._action_done()
        incoming_pickings = self.filtered(
            lambda p: p.picking_type_id.code == 'incoming' and p.state == 'done'
        )
        if incoming_pickings:
            purchase_orders = incoming_pickings.sudo().mapped('purchase_id')
            if purchase_orders:
                sale_orders = purchase_orders.sudo().mapped('ks_source_sale_order_id').filtered(
                    lambda so: so and getattr(so, 'ks_po_created_for_stock', False) and so.state not in ('sale', 'done', 'cancel')
                )
                for so in sale_orders:
                    so.sudo()._ks_check_and_notify_stock_availability()
        return result

    def button_validate(self):
        """Override button_validate to trigger inter-company lot sync before validation"""
        try:
            self.sudo()._ks_sync_intercompany_lots_between_picking()
        except Exception as e:
            _logger.warning("Failed to sync inter-company lots on button_validate: %s", str(e), exc_info=True)
        result = super().button_validate()
        return result

    def _assign_quants_by_country_fields(self):
        """Bypass quant lookup and lot/IMEI clearing on incoming receipt pickings."""
        for picking in self:
            if picking.picking_type_id and picking.picking_type_id.code == 'incoming':
                continue
            super(StockPicking, picking)._assign_quants_by_country_fields()

    def _assign_move_line_quants_by_country_fields(self, persist=True):
        """Bypass quant lookup and lot/IMEI clearing on incoming receipt pickings."""
        self.ensure_one()
        if self.picking_type_id and self.picking_type_id.code == 'incoming':
            return
        return super()._assign_move_line_quants_by_country_fields(persist=persist)

    def read(self, fields=None, load='_load_records'):
        """Override read to ensure incoming inter-company receipt pickings auto-sync move lines when opened in UI."""
        res = super().read(fields=fields, load=load)
        if not self._context.get('bin_size'):
            for picking in self:
                if picking.picking_type_id and picking.picking_type_id.code == 'incoming' and picking.state not in ('done', 'cancel'):
                    try:
                        picking.sudo()._ks_sync_intercompany_lots_between_picking()
                    except Exception as e:
                        _logger.warning("Failed to sync inter-company lots on read: %s", str(e))
        return res

    def _ks_find_linked_purchase_orders(self, sale_order):
        """Safely find Purchase Orders strictly linked to sale_order using valid ORM fields."""
        PO = self.env['purchase.order'].sudo()
        pos = PO.browse()

        if getattr(sale_order, 'auto_purchase_order_id', False):
            pos |= sale_order.auto_purchase_order_id
        if getattr(sale_order, 'ks_linked_purchase_order_id', False):
            pos |= sale_order.ks_linked_purchase_order_id

        if pos:
            return pos

        if 'ks_source_sale_order_id' in PO._fields:
            po = PO.search([('ks_source_sale_order_id', '=', sale_order.id)], limit=1)
            if po:
                return po

        if 'origin' in PO._fields and sale_order.name:
            po = PO.search([('origin', '=', sale_order.name)], limit=1)
            if po:
                return po

        return pos

    def _ks_find_linked_sale_orders(self, purchase_order):
        """Safely find Sale Orders strictly linked to purchase_order using valid ORM fields."""
        SO = self.env['sale.order'].sudo()
        sos = SO.browse()

        if getattr(purchase_order, 'auto_sale_order_id', False):
            sos |= purchase_order.auto_sale_order_id
        if getattr(purchase_order, 'ks_source_sale_order_id', False):
            sos |= purchase_order.ks_source_sale_order_id
        if getattr(purchase_order, 'ks_linked_sale_order_ids', False):
            sos |= purchase_order.ks_linked_sale_order_ids

        if sos:
            return sos

        if 'auto_purchase_order_id' in SO._fields:
            so = SO.search([('auto_purchase_order_id', '=', purchase_order.id)], limit=1)
            if so:
                return so

        if 'ks_linked_purchase_order_id' in SO._fields:
            so = SO.search([('ks_linked_purchase_order_id', '=', purchase_order.id)], limit=1)
            if so:
                return so

        if 'name' in SO._fields and purchase_order.origin:
            so = SO.search([('name', '=', purchase_order.origin)], limit=1)
            if so:
                return so

        return sos

    def _ks_sync_intercompany_lots_between_picking(self):
        """Bidirectional sync helper between delivery and receipt pickings."""
        for picking in self.sudo():
            if picking.state == 'cancel':
                continue

            if picking.picking_type_id.code == 'outgoing':
                sale_order = picking.sale_id or picking.move_ids.mapped('sale_line_id.order_id')[:1]
                if not sale_order and picking.origin:
                    sale_order = self.env['sale.order'].sudo().search([('name', '=', picking.origin)], limit=1)
                if not sale_order:
                    continue

                linked_pos = picking._ks_find_linked_purchase_orders(sale_order)
                for po in linked_pos:
                    receipt_pickings = po.picking_ids.filtered(
                        lambda p: p.picking_type_id.code == 'incoming' and p.state not in ('done', 'cancel')
                    )
                    for receipt_picking in receipt_pickings:
                        picking._ks_copy_move_lines_to_receipt(receipt_picking, po.company_id)

            elif picking.picking_type_id.code == 'incoming':
                po = picking.purchase_id or picking.move_ids.mapped('purchase_line_id.order_id')[:1]
                if not po and picking.origin:
                    po = self.env['purchase.order'].sudo().search([('name', '=', picking.origin)], limit=1)
                if not po:
                    continue

                sale_orders = picking._ks_find_linked_sale_orders(po)
                for sale_order in sale_orders:
                    delivery_pickings = sale_order.picking_ids.filtered(
                        lambda p: p.picking_type_id.code == 'outgoing' and p.state != 'cancel'
                    )
                    for delivery_picking in delivery_pickings:
                        delivery_picking._ks_copy_move_lines_to_receipt(picking, po.company_id)

    def _ks_copy_move_lines_to_receipt(self, receipt_picking, target_company):
        """Helper to copy move lines from delivery picking (self) to receipt_picking in target_company."""
        self.ensure_one()
        StockMoveLineSudo = self.env['stock.move.line'].sudo().with_context(skip_imei_lot_validation=True)
        StockLotSudo = self.env['stock.lot'].sudo().with_company(target_company.id)

        for delivery_move in self.move_ids:
            if delivery_move.state == 'cancel':
                continue
            receipt_moves = receipt_picking.move_ids.filtered(
                lambda m: m.product_id.id == delivery_move.product_id.id and m.state not in ('done', 'cancel')
            )
            if not receipt_moves:
                continue
            receipt_move = receipt_moves[0]

            delivery_lines = delivery_move.move_line_ids.filtered(
                lambda l: bool(l.lot_id or l.lot_name or getattr(l, 'imei', False) or getattr(l, 'imei2', False) or (getattr(l, 'quantity', 0.0) or getattr(l, 'qty_done', 0.0)) > 0)
            )
            if not delivery_lines:
                continue

            # Clean slate: remove existing move lines on receipt_move before recreating synced lines
            if receipt_move.move_line_ids:
                receipt_move.move_line_ids.sudo().with_context(skip_imei_lot_validation=True).unlink()

            move_line_vals_to_create = []

            for out_line in delivery_lines:
                lot_name = out_line.lot_id.sudo().name if out_line.lot_id else (out_line.lot_name or '')
                qty = getattr(out_line, 'quantity', 0.0) or getattr(out_line, 'qty_done', 0.0) or 1.0
                imei = getattr(out_line, 'imei', False) or (out_line.lot_id and getattr(out_line.lot_id.sudo(), 'imei', False))
                imei2 = getattr(out_line, 'imei2', False) or (out_line.lot_id and getattr(out_line.lot_id.sudo(), 'imei2', False))
                made_in_country_id = getattr(out_line, 'made_in_country_id', False)
                specs_made = getattr(out_line, 'specs_made', False)
                made_country = getattr(out_line, 'made_country', False)

                target_lot = False
                if lot_name:
                    target_lot = StockLotSudo.search([
                        ('product_id', '=', out_line.product_id.id),
                        ('name', '=', lot_name),
                        ('company_id', '=', target_company.id),
                    ], limit=1)
                    if not target_lot:
                        target_lot = StockLotSudo.create({
                            'name': lot_name,
                            'product_id': out_line.product_id.id,
                            'company_id': target_company.id,
                        })

                line_vals = receipt_move._prepare_move_line_vals(quantity=qty)
                line_vals.update({
                    'lot_id': target_lot.id if target_lot else False,
                    'lot_name': lot_name or (target_lot.name if target_lot else False),
                    'picked': True,
                })
                if imei:
                    line_vals['imei'] = imei
                if imei2:
                    line_vals['imei2'] = imei2
                if made_in_country_id:
                    line_vals['made_in_country_id'] = made_in_country_id.id
                if specs_made:
                    line_vals['specs_made'] = specs_made.id
                if made_country:
                    line_vals['made_country'] = made_country.id

                move_line_vals_to_create.append(line_vals)

            if move_line_vals_to_create:
                StockMoveLineSudo.create(move_line_vals_to_create)

            receipt_picking.invalidate_recordset(['move_line_ids', 'move_ids'])
            receipt_picking.move_ids.invalidate_recordset(['move_line_ids'])
