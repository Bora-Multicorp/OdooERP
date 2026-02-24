# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    imei_mismatch_count = fields.Integer(
        string="IMEI Mismatches",
        compute='_compute_imei_mismatch_count',
    )

    is_ecommerce_vendor = fields.Boolean(
        related='partner_id.is_ecommerce_vendor',
        store=True,
        readonly=True
    )

    @api.depends('move_line_ids', 'move_line_ids.is_imei_mismatch')
    def _compute_imei_mismatch_count(self):
        for picking in self:
            picking.imei_mismatch_count = len(picking.move_line_ids.filtered(lambda l: l.is_imei_mismatch))

    def button_validate(self):
        """
        Override button_validate to check IMEIs against manifest before validation.
        Only applies to incoming pickings from purchase orders.
        """
        if not self.partner_id.is_vendor or not self.partner_id.is_ecommerce_vendor:
            return super().button_validate()
        if self.env.context.get('skip_imei_validation'):

            for picking in self:
                mismatch_move_lines = self.env['stock.move.line']
                for move_line in picking.move_line_ids:
                    if not move_line.is_imei_validated and move_line.is_imei_mismatch:
                        mismatch_move_lines |= move_line
                picking._process_imei_mismatches(mismatch_move_lines)

            return super(StockPicking, self).button_validate()

        for picking in self:

            # Only check for incoming pickings with a purchase order origin
            if picking.picking_type_code == 'incoming' and picking.purchase_id:
                # initial the values
                picking.move_line_ids.write({
                    'is_imei_validated': False,
                    'is_imei_mismatch': True,
                    'imei_status': False
                })

                mismatch_data = picking._check_imei_against_manifest()
                
                if mismatch_data['mismatch_lines']:

                    # Create validation wizard with mismatch lines
                    wizard = self.env['imei.validation.wizard'].create({
                        'picking_id': picking.id,
                        'line_ids': [(0, 0, line) for line in mismatch_data['mismatch_lines']],
                    })
                    if not self.env.context.get('skip_imei_validation'):
                        return {
                            'name': _('IMEI Validation Errors'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'imei.validation.wizard',
                            'view_mode': 'form',
                            'res_id': wizard.id,
                            'target': 'new',
                        }
        
        # If no mismatches, proceed with normal validation
        return super().button_validate()

    def _process_imei_mismatches(self, mismatch_move_lines):
        """
        Process move lines that have IMEI mismatches.
        Set flag and move to On Hold location.
        """
        for move_line in mismatch_move_lines:
            move_line.action_set_imei_mismatch()

    def _check_imei_against_manifest(self):
        """
        Check scanned IMEIs against expected IMEIs from PO manifest.
        
        Returns:
            dict: Contains mismatch_lines (wizard data) and mismatch_move_lines (actual move lines)
        """
        self.ensure_one()
        mismatch_lines = []
        mismatch_move_lines = self.env['stock.move.line']
        
        if not self.purchase_id:
            return {'mismatch_lines': mismatch_lines, 'mismatch_move_lines': mismatch_move_lines}
        
        # Get all manifest lines for this PO
        manifest_lines = self.env['po.manifest.line'].search([
            ('order_id', '=', self.purchase_id.id),
            ('is_received', '=', False),
        ])
        
        # Build a lookup dictionary for manifest IMEIs by product (for backward compatibility)
        manifest_by_product = {}
        # Also build lookup by unique combination: SKU + IMEI + IMEI2
        manifest_by_sku_imei = {}
        
        # Track which manifest lines have been matched
        matched_manifest_ids = set()
        
        # Check each move line that requires IMEI validation
        for move_line in self.move_line_ids:
            # Skip already validated lines (validated and no mismatch)
            if move_line.is_imei_validated and not move_line.is_imei_mismatch:
                continue
            
            product_id = move_line.product_id.id
            product = move_line.product_id
            scanned_imei = (move_line.imei or '').strip()
            scanned_imei2 = (move_line.imei2 or '').strip()
            scanned_qty = move_line.quantity or 0.0
            scanned_sku = (product.default_code or '').strip().lower()
            
            # Check if product requires IMEI
            is_mobile = False
            is_dual_sim = False
            product_tmpl = move_line.product_id.product_tmpl_id
            product_categ = product_tmpl.categ_id
            # Mobile detection via category
            is_mobile = bool(
                product_categ
                and getattr(product_categ, 'ks_product_master.product_category_type_mobile', False)
            )

            # Dual SIM detection
            is_dual_sim = bool(getattr(product_tmpl, 'is_dual_sim', False))

            if hasattr(product_tmpl, 'is_mobile_category_selected'):
                is_mobile = product_tmpl.is_mobile_category_selected
                is_dual_sim = getattr(product_tmpl, 'is_dual_sim', False)
            else:
                # Fallback: check category name
                mobile_categ = self.env.ref('ks_product_master.product_category_type_mobile', raise_if_not_found=False)

                categ = move_line.product_id.categ_id
                while categ:
                    if categ == mobile_categ:
                        is_mobile = True
                        break
                    categ = categ.parent_id
            
            if not is_mobile:
                # Not a mobile product, skip IMEI check
                move_line.is_imei_validated = True
                continue
            

            manifest_match = None
            # Get all manifest lines for this product
            expected_manifest_lines = manifest_by_product.get(product_id, [])
            

            matching_manifest_lines = []
            
            # If no exact SKU+IMEI match, fall back to all manifest lines for this product
            # (for backward compatibility and cases where SKU might differ)
            if not matching_manifest_lines:
                matching_manifest_lines = expected_manifest_lines
            
            for manifest_line in manifest_lines:
                manifest_sku = (manifest_line.sku or '').strip().lower()

                if manifest_line.id in matched_manifest_ids:
                    continue

                if not manifest_line.product_id or not manifest_line.product_id.default_code or not manifest_line.product_id.default_code.lower() == manifest_sku:
                   continue
                
                expected_imei = (manifest_line.imei or '').strip()
                expected_imei2 = (manifest_line.imei2 or '').strip()
                expected_qty = manifest_line.qty or 0.0
                
                # Check IMEI match logic
                is_match = self._compare_imei(
                    scanned_imei, scanned_imei2,
                    scanned_qty , expected_qty,
                    expected_imei, expected_imei2,
                    is_dual_sim
                )
                
                if is_match:
                    move_line.write({'imei_status': 'pass'})
                    move_line.is_imei_mismatch = False
                    move_line.is_imei_validated = True
                    manifest_match = manifest_line
                    matched_manifest_ids.add(manifest_line.id)
                    break


        for move_line in self.move_line_ids:
            if not move_line.is_imei_validated and move_line.is_imei_mismatch:
                mismatch_lines.append({
                    'product_id': move_line.product_id.id,
                    'scanned_imei': move_line.imei,
                    'scanned_imei2': move_line.imei2,
                    'mismatch_type': 'wrong',
                })

                mismatch_move_lines |= move_line

        # If validation passes for all lines, mark manifest lines as received
        if not mismatch_lines:
            self._mark_manifest_lines_received(matched_manifest_ids)
        
        return {
            'mismatch_lines': mismatch_lines,
            'mismatch_move_lines': mismatch_move_lines,
        }

    def _compare_imei(self, scanned_imei, scanned_imei2,scanned_qty, expected_qty, expected_imei, expected_imei2, is_dual_sim):
        """
        Compare scanned IMEIs against expected IMEIs.
        
        For dual-SIM devices:
            Valid if (imei == expected_imei AND imei2 == expected_imei2)
               OR   (imei == expected_imei2 AND imei2 == expected_imei)
        
        For single-SIM devices:
            scanned_imei must match expected_imei
        """
        if is_dual_sim and expected_imei2:

            match_normal = (scanned_imei == expected_imei and scanned_imei2 == expected_imei2)
            if match_normal:
                match_normal = (scanned_qty == expected_qty)
            # match_swapped = (scanned_imei == expected_imei2 and scanned_imei2 == expected_imei)
            return match_normal
        else:
            return scanned_imei == expected_imei

    def _mark_manifest_lines_received(self, manifest_line_ids):
        """Mark manifest lines as received after successful validation."""
        if manifest_line_ids:
            manifest_lines = self.env['po.manifest.line'].browse(list(manifest_line_ids))
            manifest_lines.write({'is_received': True})

    def action_view_imei_mismatches(self):
        """Open view showing all IMEI mismatch lines for this picking."""
        self.ensure_one()
        return {
            'name': _('IMEI Mismatches'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move.line',
            'view_mode': 'list,form',
            'domain': [('picking_id', '=', self.id), ('is_imei_mismatch', '=', True)],
            'context': {'default_picking_id': self.id},
        }
