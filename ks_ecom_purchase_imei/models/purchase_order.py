# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    manifest_line_ids = fields.One2many(
        comodel_name='po.manifest.line',
        inverse_name='order_id',
        string="Manifest Lines",
    )
    
    manifest_line_count = fields.Integer(
        string="Manifest Lines Count",
        compute='_compute_manifest_line_count',
    )

    is_ecommerce_vendor = fields.Boolean(
        related='partner_id.is_ecommerce_vendor',
        store=True,
        readonly=True
    )

    sla_status = fields.Selection([
        ('on_time', 'On Time'),
        ('breached', 'Breached'),
    ], default='on_time', tracking=True)

    @api.depends('manifest_line_ids')
    def _compute_manifest_line_count(self):
        for order in self:
            order.manifest_line_count = len(order.manifest_line_ids)

    def action_open_manifest_upload_wizard(self):
        """Open the manifest upload wizard."""
        self.ensure_one()
        return {
            'name': 'Upload Manifest',
            'type': 'ir.actions.act_window',
            'res_model': 'manifest.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_is_multi_po': False,
            },
        }

    def action_open_multi_po_manifest_upload_wizard(self):
        """Open the manifest upload wizard for multiple purchase orders."""
        if not self:
            raise UserError(_("Please select at least one Purchase Order."))
        
        # Validate that all selected POs are in draft state
        non_draft_orders = self.filtered(lambda po: po.state != 'draft')
        if non_draft_orders:
            order_names = ', '.join(non_draft_orders.mapped('name'))
            raise UserError(
                _("Manifest can only be imported for Purchase Orders in draft state.\n\n"
                  "The following Purchase Orders are not in draft state: %s") % order_names
            )
        
        # Get order IDs and names for context
        order_ids = self.ids
        order_names = {po.id: po.name for po in self}
        
        return {
            'name': 'Upload Manifest (Multiple POs)',
            'type': 'ir.actions.act_window',
            'res_model': 'manifest.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_is_multi_po': True,
                'default_order_ids': order_ids,
                'order_names': order_names,
            },
        }

    def action_view_manifest_lines(self):
        """Open the manifest lines tree view for this PO."""
        self.ensure_one()
        return {
            'name': 'Manifest Lines',
            'type': 'ir.actions.act_window',
            'res_model': 'po.manifest.line',
            'view_mode': 'list,form',
            'domain': [('order_id', '=', self.id)],
            'context': {
                'default_order_id': self.id,
            },
        }

    def action_import_manifest_from_receipts(self):
        """
        Import manifest lines from stock.move.line data for selected purchase orders.
        Pulls data (Product SKU, Qty, IMEI 1, IMEI 2) from stock.move.line into po.manifest.line.
        Each manifest line correctly links back to its specific purchase_order_id.
        
        Handles both single PO (form view) and multiple POs (tree view selection).
        """
        if not self:
            raise UserError(_("Please select at least one Purchase Order."))
        
        manifest_lines_created = 0
        errors = []
        orders_processed = []
        
        for order in self:
            # Get all stock move lines from receipts related to this PO
            # Find pickings related to this PO
            pickings = self.env['stock.picking'].search([
                ('purchase_id', '=', order.id),
                ('picking_type_code', '=', 'incoming'),
                ('state', 'in', ['draft', 'waiting', 'confirmed', 'assigned', 'done'])
            ])
            
            if not pickings:
                errors.append(_("No receipts found for PO %s.") % order.name)
                continue
            
            # Get all move lines from these pickings
            move_lines = pickings.mapped('move_line_ids').filtered(
                lambda ml: ml.product_id and ml.show_imei_fields and ml.imei
            )
            
            if not move_lines:
                errors.append(_("No IMEI data found in receipts for PO %s.") % order.name)
                continue
            
            # Delete existing manifest lines for this order (optional - you may want to keep them)
            # Uncomment if you want to replace existing manifest
            # existing_lines = self.env['po.manifest.line'].search([('order_id', '=', order.id)])
            # existing_lines.unlink()
            
            # Create manifest lines from move lines
            manifest_vals_list = []
            seen_combinations = set()  # Track unique combinations to avoid duplicates
            
            for move_line in move_lines:
                product = move_line.product_id
                sku = product.default_code or ''
                imei = (move_line.imei or '').strip()
                imei2 = (move_line.imei2 or '').strip()
                qty = int(move_line.quantity or 1)
                
                if not sku or not imei:
                    continue
                
                # Create unique key: SKU + IMEI + IMEI2 (when dual sim)
                # This ensures duplicate products with different IMEIs are treated as distinct
                unique_key = (order.id, sku, imei, imei2)
                
                if unique_key in seen_combinations:
                    # Skip if we've already created this exact combination
                    continue
                
                seen_combinations.add(unique_key)
                
                # Check if manifest line already exists for this combination
                existing = self.env['po.manifest.line'].search([
                    ('order_id', '=', order.id),
                    ('sku', '=', sku),
                    ('imei', '=', imei),
                    ('imei2', '=', imei2),
                ], limit=1)
                
                if existing:
                    # Update quantity if needed
                    if existing.qty != qty:
                        existing.qty = qty
                    continue
                
                manifest_vals_list.append({
                    'order_id': order.id,
                    'product_id': product.id,
                    'sku': sku,
                    'imei': imei,
                    'imei2': imei2,
                    'qty': qty,
                })
            
            if manifest_vals_list:
                try:
                    self.env['po.manifest.line'].create(manifest_vals_list)
                    manifest_lines_created += len(manifest_vals_list)
                    orders_processed.append(order.name)
                except Exception as e:
                    errors.append(_("Error creating manifest lines for PO %s: %s") % (order.name, str(e)))
        
        # Show result message
        if manifest_lines_created > 0:
            message = _("Successfully imported %d manifest line(s) from %d Purchase Order(s).") % (
                manifest_lines_created, len(orders_processed)
            )
        else:
            message = _("No manifest lines were imported.")
        
        if errors:
            message += "\n\n" + _("Warnings:") + "\n" + "\n".join(errors)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Manifest'),
                'message': message,
                'type': 'success' if manifest_lines_created > 0 else 'warning',
                'sticky': len(errors) > 0,
            }
        }
