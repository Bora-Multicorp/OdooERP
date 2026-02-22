# -*- coding: utf-8 -*-

import base64
import csv
import io

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ManifestUploadWizard(models.TransientModel):
    _name = 'manifest.upload.wizard'
    _description = 'Manifest Upload Wizard'

    order_id = fields.Many2one(
        comodel_name='purchase.order',
        string="Purchase Order",
        readonly=True,
        help="Single Purchase Order (for single PO import mode)",
    )
    
    is_multi_po = fields.Boolean(
        string="Multi-PO Import",
        default=False,
        help="If True, import manifest for multiple purchase orders",
    )
    
    order_ids = fields.Many2many(
        comodel_name='purchase.order',
        string="Purchase Orders",
        readonly=True,
        help="Multiple Purchase Orders (for multi-PO import mode)",
    )
    
    file_data = fields.Binary(
        string="CSV File",
        required=True,
        help="Upload a CSV file. For single PO: SKU, IMEI, IMEI2 (optional), Qty. "
             "For multi-PO: PO Name, SKU, IMEI, IMEI2 (optional), Qty",
    )
    
    file_name = fields.Char(
        string="File Name",
    )
    
    preview_line_ids = fields.One2many(
        comodel_name='manifest.upload.preview.line',
        inverse_name='wizard_id',
        string="Preview Lines",
    )
    
    state = fields.Selection([
        ('upload', 'Upload'),
        ('preview', 'Preview'),
    ], default='upload', string="State")
    
    total_lines = fields.Integer(
        string="Total Lines",
        compute='_compute_totals',
    )

    @api.depends('preview_line_ids')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_lines = len(wizard.preview_line_ids)
    
    def _find_product_by_sku(self, sku):
        """
        Search for a product globally by SKU (default_code).
        First tries to find in product.product, then falls back to product.template if needed.
        
        :param sku: The SKU/default_code to search for
        :return: product.product record or False if not found
        """
        if not sku or not sku.strip():
            return False
        
        sku_clean = sku.strip()
        
        # Search in product.product by default_code
        product = self.env['product.product'].search([
            ('default_code', '=', sku_clean)
        ], limit=1)
        
        if product:
            return product
        
        # Fallback: search in product.template by default_code
        # (in case product.product doesn't exist but template does)
        template = self.env['product.template'].search([
            ('default_code', '=', sku_clean)
        ], limit=1)
        
        if template:
            # Get the first variant or create a default variant reference
            # Usually we want product.product, so try to get it from template
            if template.product_variant_ids:
                return template.product_variant_ids[0]
        
        return False


    @api.constrains('file_name')
    def _check_file_extension(self):
        for wizard in self:
            if wizard.file_name and not wizard.file_name.lower().endswith('.csv'):
                raise ValidationError(_("Only CSV files are allowed."))
    

    def action_parse_csv(self):
        """Parse the uploaded CSV file and show preview."""
        self.ensure_one()
        
        # Validate order selection
        if self.is_multi_po:
            if not self.order_ids:
                raise UserError(_("Please select at least one Purchase Order for multi-PO import."))
        else:
            if not self.order_id:
                raise UserError(_("Please select a Purchase Order for single PO import."))
        
        if not self.file_data:
            raise UserError(_("Please upload a CSV file."))
        
        if self.file_name and not self.file_name.lower().endswith('.csv'):
            raise UserError(_("Only CSV files are allowed."))
        
        # Decode the file
        try:
            file_content = base64.b64decode(self.file_data)
            # Try different encodings
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    file_string = file_content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise UserError(_("Unable to decode the CSV file. Please ensure it's a valid CSV file."))
        except Exception as e:
            raise UserError(_("Error reading file: %s") % str(e))
        
        # Parse CSV
        preview_lines = []
        try:
            csv_file = io.StringIO(file_string)
            reader = csv.DictReader(csv_file)
            
            # Normalize header names (lowercase, strip whitespace)
            if reader.fieldnames:
                reader.fieldnames = [name.strip().lower() for name in reader.fieldnames]
            
            if self.is_multi_po:
                # Multi-PO mode: First column should be PO Name
                required_columns = ['po name', 'po_name', 'purchase order', 'purchase_order', 'sku', 'imei']
                # Check if we have PO name column (any variation)
                has_po_column = any(col in (reader.fieldnames or []) for col in ['po name', 'po_name', 'purchase order', 'purchase_order'])
                if not has_po_column:
                    raise UserError(
                        _("Missing required column: PO Name\n\n"
                          "For multi-PO import, CSV must have columns: PO Name, SKU, IMEI, IMEI2 (optional), Qty")
                    )
                
                # Get order names from context or from selected orders
                order_names = self.env.context.get('order_names', {})
                if not order_names:
                    order_names = {po.id: po.name for po in self.order_ids}
                
                # Build lookup for orders by name
                orders_by_name = {}
                for order in self.order_ids:
                    orders_by_name[order.name.lower()] = order
                    # Also add without spaces/dashes for flexibility
                    orders_by_name[order.name.replace(' ', '').replace('-', '').lower()] = order
                
                # Build lookup for PO lines by SKU for each order
                po_lines_by_order_sku = {}
                for order in self.order_ids:
                    po_lines_by_order_sku[order.id] = {}
                    for po_line in order.order_line:
                        sku = po_line.product_id.default_code
                        if sku:
                            sku_lower = sku.strip().lower()
                            if sku_lower not in po_lines_by_order_sku[order.id]:
                                po_lines_by_order_sku[order.id][sku_lower] = po_line
                
                line_number = 1
                for row in reader:
                    line_number += 1
                    
                    # Get PO name from various possible column names
                    po_name = (row.get('po name') or row.get('po_name') or 
                              row.get('purchase order') or row.get('purchase_order') or '').strip()
                    
                    sku = (row.get('sku') or '').strip()
                    imei = (row.get('imei') or '').strip()
                    imei2 = (row.get('imei2') or row.get('imei 2') or '').strip()
                    qty_str = (row.get('qty') or row.get('quantity') or '1').strip()
                    
                    # Skip empty rows
                    if not po_name and not sku and not imei:
                        continue
                    
                    # Validate PO name
                    if not po_name:
                        raise UserError(_("Line %d: PO Name is required for multi-PO import.") % line_number)
                    
                    # Find matching order
                    po_name_lower = po_name.lower()
                    order = orders_by_name.get(po_name_lower) or orders_by_name.get(po_name_lower.replace(' ', '').replace('-', ''))
                    
                    if not order:
                        raise UserError(
                            _("Line %d: Purchase Order '%s' not found in selected orders.\n\n"
                              "Please ensure the PO name in the CSV matches one of the selected Purchase Orders.") 
                            % (line_number, po_name)
                        )
                    
                    # Validate IMEI
                    if not imei:
                        raise UserError(_("Line %d: IMEI is required.") % line_number)
                    
                    # Parse quantity
                    try:
                        qty = int(qty_str) if qty_str else 1
                    except ValueError:
                        qty = 1
                    
                    # Find matching PO line
                    sku_lower = sku.lower()
                    po_line = None
                    product_id = False
                    
                    if order.id in po_lines_by_order_sku:
                        po_line = po_lines_by_order_sku[order.id].get(sku_lower)
                    
                    # Get product_id from PO line if available
                    if po_line and po_line.product_id:
                        product_id = po_line.product_id.id
                    else:
                        # Fallback: Search globally for product by SKU
                        product = self._find_product_by_sku(sku)
                        if product:
                            product_id = product.id
                    
                    preview_lines.append({
                        'wizard_id': self.id,
                        'order_id': order.id,
                        'sku': sku,
                        'imei': imei,
                        'imei2': imei2,
                        'qty': qty,
                        'product_id': product_id,
                    })
            else:
                # Single PO mode: Original logic
                required_columns = ['sku', 'imei']
                missing_columns = [col for col in required_columns if col not in (reader.fieldnames or [])]
                if missing_columns:
                    raise UserError(
                        _("Missing required columns: %s\n\nExpected columns: SKU, IMEI, IMEI2 (optional), Qty")
                        % ', '.join(missing_columns)
                    )
                
                # Build lookup for PO lines by SKU
                po_lines_by_sku = {}
                for po_line in self.order_id.order_line:
                    sku = po_line.product_id.default_code
                    if sku:
                        sku_lower = sku.strip().lower()
                        if sku_lower not in po_lines_by_sku:
                            po_lines_by_sku[sku_lower] = po_line
                
                line_number = 1
                for row in reader:
                    line_number += 1
                    
                    sku = (row.get('sku') or '').strip()
                    imei = (row.get('imei') or '').strip()
                    imei2 = (row.get('imei2') or row.get('imei 2') or '').strip()
                    qty_str = (row.get('qty') or row.get('quantity') or '1').strip()
                    
                    # Skip empty rows
                    if not sku and not imei:
                        continue
                    
                    # Validate IMEI
                    if not imei:
                        raise UserError(_("Line %d: IMEI is required.") % line_number)
                    
                    # Parse quantity
                    try:
                        qty = int(qty_str) if qty_str else 1
                    except ValueError:
                        qty = 1
                    
                    # Find matching PO line
                    sku_lower = sku.lower()
                    po_line = po_lines_by_sku.get(sku_lower)
                    product_id = False
                    
                    # Get product_id from PO line if available
                    if po_line and po_line.product_id:
                        product_id = po_line.product_id.id
                    else:
                        # Fallback: Search globally for product by SKU
                        product = self._find_product_by_sku(sku)
                        if product:
                            product_id = product.id
                    
                    preview_lines.append({
                        'wizard_id': self.id,
                        'order_id': self.order_id.id,
                        'sku': sku,
                        'imei': imei,
                        'imei2': imei2,
                        'qty': qty,
                        'product_id': product_id,
                    })
        
        except csv.Error as e:
            raise UserError(_("CSV parsing error: %s") % str(e))
        
        if not preview_lines:
            raise UserError(_("No valid lines found in the CSV file."))
        
        # Clear existing preview lines and create new ones
        self.preview_line_ids.unlink()
        self.env['manifest.upload.preview.line'].create(preview_lines)
        
        self.state = 'preview'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'manifest.upload.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_confirm_upload(self):
        """Confirm and create manifest lines from preview."""
        self.ensure_one()
        
        if not self.preview_line_ids:
            raise UserError(_("No lines to import."))

        # Check for duplicate IMEIs per order
        if self.is_multi_po:
            # Check duplicates per order
            for order in self.order_ids:
                order_lines = self.preview_line_ids.filtered(lambda l: l.order_id.id == order.id)
                imeis = order_lines.mapped('imei')
                if len(imeis) != len(set(imeis)):
                    raise UserError(
                        _("Duplicate IMEIs found for Purchase Order %s. Each IMEI must be unique per order.") 
                        % order.name
                    )
        else:
            # Check duplicates for single order
            imeis = self.preview_line_ids.mapped('imei')
            if len(imeis) != len(set(imeis)):
                raise UserError(_("Duplicate IMEIs found in the CSV file. Each IMEI must be unique."))

        # Group preview lines by order_id
        lines_by_order = {}
        for preview_line in self.preview_line_ids:
            order_id = preview_line.order_id.id
            if order_id not in lines_by_order:
                lines_by_order[order_id] = []
            lines_by_order[order_id].append(preview_line)
        
        # Create manifest lines for each order
        total_created = 0
        orders_processed = []
        
        for order_id, lines in lines_by_order.items():
            order = self.env['purchase.order'].browse(order_id)
            
            # Delete existing manifest lines for this order
            old_lines = self.env['po.manifest.line'].search([
                ('order_id', '=', order_id)
            ])
            old_lines.unlink()

            manifest_vals = []
            for preview_line in lines:
                manifest_vals.append({
                    'order_id': order_id,
                    'product_id': preview_line.product_id.id,
                    'sku': preview_line.sku,
                    'imei': preview_line.imei,
                    'imei2': preview_line.imei2,
                    'qty': preview_line.qty,
                })
            
            if manifest_vals:
                self.env['po.manifest.line'].create(manifest_vals)
                total_created += len(manifest_vals)
                orders_processed.append(order.name)
        
        message = _('%d manifest line(s) imported successfully for %d Purchase Order(s).') % (
            total_created, len(orders_processed)
        )
        if len(orders_processed) > 1:
            message += '\n\n' + _('Orders: %s') % ', '.join(orders_processed)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_back_to_upload(self):
        """Go back to upload state."""
        self.ensure_one()
        self.preview_line_ids.unlink()
        self.state = 'upload'
        self.file_data = False
        self.file_name = False
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'manifest.upload.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


class ManifestUploadPreviewLine(models.TransientModel):
    _name = 'manifest.upload.preview.line'
    _description = 'Manifest Upload Preview Line'

    wizard_id = fields.Many2one(
        comodel_name='manifest.upload.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade',
    )
    
    order_id = fields.Many2one(
        comodel_name='purchase.order',
        string="Purchase Order",
        readonly=True,
        help="Purchase Order this line belongs to",
    )
    
    sku = fields.Char(
        string="SKU",
        readonly=True,
    )
    
    imei = fields.Char(
        string="IMEI",
        readonly=True,
    )
    
    imei2 = fields.Char(
        string="IMEI 2",
        readonly=True,
    )
    
    qty = fields.Integer(
        string="Qty",
        readonly=True,
    )

    
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        readonly=True,
    )
    
    is_matched = fields.Boolean(
        string="Matched",
        readonly=True,
    )

