# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Additional packing list fields
    ks_exporter_ref = fields.Char(string="Exporter's Ref")
    ks_other_reference = fields.Char(string="Other Reference(s)")
    ks_supplier_reference = fields.Char(string="Supplier's Reference")
    ks_reference_no_date = fields.Char(string="Reference No. and Date")
    ks_country_of_origin = fields.Char(string="Country of Origin of Goods", default="INDIA")
    ks_country_of_final_destination = fields.Char(string="Country of Final Destination")
    ks_terms_of_delivery_payment = fields.Char(string="Terms of Delivery & Payment")
    ks_pre_carriage_by = fields.Char(string="Pre-Carriage by")
    ks_place_of_receipt_by_pre_carrier = fields.Char(string="Place of Receipt by Pre-Carrier")
    ks_vessel_flight_no = fields.Char(string="Vessel / Flight No.")
    ks_port_of_loading = fields.Char(string="Port of Loading")
    ks_port_of_discharge = fields.Char(string="Port of Discharge")
    ks_final_destination = fields.Char(string="Final Destination")
    ks_gross_weight = fields.Char(string="Gross Weight")
    ks_net_weight = fields.Char(string="Net Weight")
    # User signature for packing list PDF
    ks_user_signature = fields.Binary(string="User Signature", attachment=True)
    # Terms of Delivery fields
    ks_contact_date = fields.Date(string="Contact Date")
    ks_contact_no = fields.Char(string="Contact No")
    ks_lut_no = fields.Char(string="LUT No")
    ks_lut_date = fields.Date(string="Date")

    def get_invoice_info(self):
        """Get invoice information from related sale order"""
        self.ensure_one()
        invoice_info = {
            'invoice_no': '',
            'invoice_date': False,
        }
        
        # Try to get invoice from sale order
        if self.sale_id:
            # Get invoices from sale order
            invoices = self.sale_id.invoice_ids.filtered(lambda inv: inv.state in ('posted', 'draft'))
            if invoices:
                invoice = invoices[0]
                invoice_info['invoice_no'] = invoice.name or ''
                invoice_info['invoice_date'] = invoice.invoice_date or invoice.date or False
            # Fallback: use sale order name and date
            elif not invoice_info['invoice_no']:
                invoice_info['invoice_no'] = self.sale_id.name or ''
                invoice_info['invoice_date'] = self.sale_id.date_order or False
        
        # Try to get from origin if it's an invoice reference
        if not invoice_info['invoice_no'] and self.origin:
            # Check if origin is an invoice
            invoice = self.env['account.move'].search([
                ('name', '=', self.origin),
                ('move_type', 'in', ('out_invoice', 'out_refund'))
            ], limit=1)
            if invoice:
                invoice_info['invoice_no'] = invoice.name or ''
                invoice_info['invoice_date'] = invoice.invoice_date or invoice.date or False
        
        return invoice_info

    def get_exporter_info(self):
        """Get exporter (company) information"""
        self.ensure_one()
        company = self.company_id
        partner = company.partner_id if company else False
        
        exporter_info = {
            'name': company.name or '' if company else '',
            'address': '',
            'gst': company.vat or '' if company else '',
            'iec': '',
        }
        
        if partner:
            address_parts = []
            if partner.street:
                address_parts.append(partner.street)
            if partner.street2:
                address_parts.append(partner.street2)
            if partner.city:
                address_parts.append(partner.city)
            if partner.state_id:
                address_parts.append(partner.state_id.name)
            if partner.zip:
                address_parts.append(partner.zip)
            if partner.country_id:
                address_parts.append(partner.country_id.name)
            
            exporter_info['address'] = ', '.join(address_parts)
            
            # Try to get IEC code (custom field, may not exist)
            try:
                if hasattr(partner, 'iec_code') and partner.iec_code:
                    exporter_info['iec'] = partner.iec_code
            except:
                pass
        
        return exporter_info

    def get_consignee_info(self):
        """Get consignee information"""
        self.ensure_one()
        # Consignee is typically the shipping partner
        consignee_partner = self.partner_id
        
        consignee_info = {
            'name': '',
            'address': '',
        }
        
        if consignee_partner:
            consignee_info['name'] = consignee_partner.name or ''
            
            address_parts = []
            if consignee_partner.street:
                address_parts.append(consignee_partner.street)
            if consignee_partner.street2:
                address_parts.append(consignee_partner.street2)
            if consignee_partner.city:
                address_parts.append(consignee_partner.city)
            if consignee_partner.state_id:
                address_parts.append(consignee_partner.state_id.name)
            if consignee_partner.zip:
                address_parts.append(consignee_partner.zip)
            if consignee_partner.country_id:
                address_parts.append(consignee_partner.country_id.name)
            
            consignee_info['address'] = ', '.join(address_parts)
        
        return consignee_info

    def get_buyer_info(self):
        """Get buyer information (if different from consignee)"""
        self.ensure_one()
        # Buyer is typically from sale order partner
        buyer_partner = False
        
        if self.sale_id:
            buyer_partner = self.sale_id.partner_id
        elif self.partner_id:
            buyer_partner = self.partner_id
        
        buyer_info = {
            'name': '',
            'address': '',
        }
        
        if buyer_partner:
            buyer_info['name'] = buyer_partner.name or ''
            
            address_parts = []
            if buyer_partner.street:
                address_parts.append(buyer_partner.street)
            if buyer_partner.street2:
                address_parts.append(buyer_partner.street2)
            if buyer_partner.city:
                address_parts.append(buyer_partner.city)
            if buyer_partner.state_id:
                address_parts.append(buyer_partner.state_id.name)
            if buyer_partner.zip:
                address_parts.append(buyer_partner.zip)
            if buyer_partner.country_id:
                address_parts.append(buyer_partner.country_id.name)
            
            buyer_info['address'] = ', '.join(address_parts)
        
        return buyer_info

    def get_packing_list_lines(self):
        """Get packing list line items. Uses move-level manual fields (x_dimensions, x_package_info, x_line_remark) when set."""
        self.ensure_one()
        lines = []

        package_levels = self.package_level_ids
        if package_levels:
            for idx, package_level in enumerate(package_levels, 1):
                move_lines = package_level.move_line_ids.filtered(lambda ml: ml.product_id)
                moves = move_lines.mapped('move_id')

                # Dimensions: prefer first move's manual x_dimensions
                dimensions = ''
                try:
                    if hasattr(package_level, 'package_id') and package_level.package_id:
                        package = package_level.package_id
                        if hasattr(package, 'pack_length') and hasattr(package, 'pack_width') and hasattr(package, 'pack_height'):
                            if package.pack_length and package.pack_width and package.pack_height:
                                dimensions = f"{package.pack_length}*{package.pack_width}*{package.pack_height}"
                except Exception:
                    pass

                invoice_ref = ''
                invoice_info = self.get_invoice_info()
                if invoice_info.get('invoice_no'):
                    invoice_ref = invoice_info.get('invoice_no', '')

                box_count = len(move_lines) if move_lines else 0
                box_range = f"(1-{box_count})" if box_count > 0 else ""

                dim_parts = [f"PALLET NO.{idx}"]
                if box_count > 0:
                    dim_parts.append(f"{box_count} BOXES {box_range}")
                if invoice_ref:
                    dim_parts.append(invoice_ref)
                if dimensions:
                    dim_parts.append(f"DIMENSION- {dimensions}")
                dimensions_text = ", ".join(dim_parts)

                # Use move-level manual fields when available (first move in package)
                manual_dim = moves[0].x_dimensions if moves and moves[0].x_dimensions else None
                manual_boxes = moves[0].x_package_info if moves and moves[0].x_package_info else None
                manual_remarks = moves[0].x_line_remark if moves and moves[0].x_line_remark else None
                if manual_dim:
                    dimensions_text = manual_dim
                if manual_boxes:
                    boxes_text = manual_boxes
                else:
                    boxes_text = f"{box_count} BOXES {box_range}" if box_count > 0 else ''

                descriptions = []
                quantities = []
                total_qty = 0
                for move_line in move_lines:
                    if move_line.product_id:
                        product_name = move_line.product_id.name
                        origin_text = ''
                        try:
                            if hasattr(move_line.product_id, 'country_of_origin') and move_line.product_id.country_of_origin:
                                origin_text = f"Made in {move_line.product_id.country_of_origin.name}"
                        except Exception:
                            pass
                        descriptions.append(product_name)
                        if origin_text:
                            descriptions.append(origin_text)
                        qty = int(move_line.quantity or 0)
                        quantities.append(str(qty))
                        total_qty += qty

                line_info = {
                    'dimensions': dimensions_text,
                    'boxes': boxes_text,
                    'description': '<br/>'.join(descriptions) if descriptions else '',
                    'description_list': descriptions,
                    'quantity': '<br/>'.join(quantities) if quantities else '',
                    'quantity_list': quantities,
                    'total_quantity': total_qty,
                    'remarks': manual_remarks if manual_remarks else (f"{total_qty}*1 = {total_qty}" if total_qty > 0 else ''),
                }
                lines.append(line_info)
        else:
            # No packages: one row per move, use move-level manual fields
            for move in self.move_ids:
                if not move.product_id:
                    continue
                product = move.product_id
                qty = int(move.product_qty or 0)
                origin_text = ''
                try:
                    if hasattr(product, 'country_of_origin') and product.country_of_origin:
                        origin_text = f"Made in {product.country_of_origin.name}"
                except Exception:
                    pass
                descriptions = [product.name]
                if origin_text:
                    descriptions.append(origin_text)

                line_info = {
                    'dimensions': move.x_dimensions or '',
                    'boxes': move.x_package_info or '1 BOX',
                    'description': '<br/>'.join(descriptions),
                    'description_list': descriptions,
                    'quantity': str(qty),
                    'quantity_list': [str(qty)],
                    'total_quantity': qty,
                    'remarks': move.x_line_remark or '',
                }
                lines.append(line_info)

        return lines

    def get_packing_list_totals(self):
        """Get total packages, quantity, and weights"""
        self.ensure_one()
        totals = {
            'total_packages': 0,
            'total_boxes': 0,
            'total_quantity': 0,
            'gross_weight': 0.0,
            'net_weight': 0.0,
        }
        
        # Count packages
        package_levels = self.package_level_ids
        if package_levels:
            totals['total_packages'] = len(package_levels)
            for package_level in package_levels:
                totals['gross_weight'] += package_level.weight or 0.0
                move_lines = package_level.move_line_ids
                totals['total_boxes'] += len(move_lines)
                for move_line in move_lines:
                    if move_line.product_id:
                        totals['total_quantity'] += int(move_line.quantity or 0)
                        if move_line.product_id.weight:
                            totals['net_weight'] += (move_line.product_id.weight * (move_line.quantity or 0))
        else:
            # No packages, count move lines
            totals['total_boxes'] = len(self.move_line_ids)
            for move_line in self.move_line_ids:
                if move_line.product_id:
                    totals['total_quantity'] += int(move_line.quantity or 0)
                    if move_line.product_id.weight:
                        weight = move_line.product_id.weight * (move_line.quantity or 0)
                        totals['net_weight'] += weight
                        totals['gross_weight'] += weight * 1.1  # Approximate
        
        return totals

