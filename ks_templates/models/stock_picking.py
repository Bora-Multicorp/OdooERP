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
    ks_no_kin_of_pkg  = fields.Char(string="No. and Kind of Pkg ")
    ks_remark = fields.Text(string="Remark")
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
        """Get packing list line items - one row per package with all products in description column"""
        self.ensure_one()
        lines = []
        
        # Group by package if available, otherwise by product
        package_levels = self.package_level_ids
        if package_levels:
            # Process by packages - one row per package with all products
            for idx, package_level in enumerate(package_levels, 1):
                move_lines = package_level.move_line_ids.filtered(lambda ml: ml.product_id)
                
                # Get package dimensions if available
                dimensions = ''
                try:
                    if hasattr(package_level, 'package_id') and package_level.package_id:
                        package = package_level.package_id
                        if hasattr(package, 'pack_length') and hasattr(package, 'pack_width') and hasattr(package, 'pack_height'):
                            if package.pack_length and package.pack_width and package.pack_height:
                                dimensions = f"{package.pack_length}*{package.pack_width}*{package.pack_height}"
                except:
                    pass
                
                # Get invoice reference for package
                invoice_ref = ''
                invoice_info = self.get_invoice_info()
                if invoice_info.get('invoice_no'):
                    invoice_ref = invoice_info.get('invoice_no', '')
                
                # Count boxes
                box_count = len(move_lines) if move_lines else 0
                box_range = f"(1-{box_count})" if box_count > 0 else ""
                
                # Build dimensions text
                dim_parts = [f"PALLET NO.{idx}"]
                if box_count > 0:
                    dim_parts.append(f"{box_count} BOXES {box_range}")
                if invoice_ref:
                    dim_parts.append(invoice_ref)
                if dimensions:
                    dim_parts.append(f"DIMENSION- {dimensions}")
                dimensions_text = ", ".join(dim_parts)
                
                # Build description with all products (multi-line format)
                descriptions = []
                quantities = []
                total_qty = 0
                
                for move_line in move_lines:
                    if move_line.product_id:
                        product_name = move_line.product_id.name
                        # Try to get country of origin from product
                        origin_text = ''
                        try:
                            if hasattr(move_line.product_id, 'country_of_origin') and move_line.product_id.country_of_origin:
                                origin_text = f"Made in {move_line.product_id.country_of_origin.name}"
                        except:
                            pass
                        
                        # Add product name
                        descriptions.append(product_name)
                        # Add origin if available
                        if origin_text:
                            descriptions.append(origin_text)
                        
                        qty = int(move_line.qty_done or move_line.reserved_uom_qty or 0)
                        quantities.append(str(qty))
                        total_qty += qty
                
                # Format descriptions and quantities as HTML with line breaks
                description_html = '<br/>'.join(descriptions) if descriptions else ''
                quantity_html = '<br/>'.join(quantities) if quantities else ''
                
                # Create single row for this package
                line_info = {
                    'dimensions': dimensions_text,
                    'boxes': f"{box_count} BOXES {box_range}" if box_count > 0 else '',
                    'description': description_html,  # HTML formatted with <br/>
                    'description_list': descriptions,  # Keep list for template iteration
                    'quantity': quantity_html,  # HTML formatted with <br/>
                    'quantity_list': quantities,  # Keep list for template iteration
                    'total_quantity': total_qty,
                    'remarks': f"{total_qty}*1 = {total_qty}" if total_qty > 0 else '',
                }
                lines.append(line_info)
        else:
            # Process by move lines (no packages) - group by product
            product_groups = {}
            for move_line in self.move_line_ids:
                if move_line.product_id:
                    product = move_line.product_id
                    if product.id not in product_groups:
                        product_groups[product.id] = {
                            'product': product,
                            'quantity': 0,
                            'move_lines': []
                        }
                    product_groups[product.id]['quantity'] += int(move_line.qty_done or move_line.reserved_uom_qty or 0)
                    product_groups[product.id]['move_lines'].append(move_line)
            
            # Create rows for each product group
            for product_id, group_data in product_groups.items():
                product = group_data['product']
                qty = group_data['quantity']
                
                # Get country of origin
                origin_text = ''
                try:
                    if hasattr(product, 'country_of_origin') and product.country_of_origin:
                        origin_text = f"Made in {product.country_of_origin.name}"
                except:
                    pass
                
                descriptions = [product.name]
                if origin_text:
                    descriptions.append(origin_text)
                
                description_html = '<br/>'.join(descriptions) if descriptions else ''
                
                line_info = {
                    'dimensions': '',
                    'boxes': '1 BOX',
                    'description': description_html,
                    'description_list': descriptions,
                    'quantity': str(qty),
                    'quantity_list': [str(qty)],
                    'total_quantity': qty,
                    'remarks': '',
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
                        totals['total_quantity'] += int(move_line.qty_done or move_line.reserved_uom_qty or 0)
                        if move_line.product_id.weight:
                            totals['net_weight'] += (move_line.product_id.weight * (move_line.qty_done or move_line.reserved_uom_qty or 0))
        else:
            # No packages, count move lines
            totals['total_boxes'] = len(self.move_line_ids)
            for move_line in self.move_line_ids:
                if move_line.product_id:
                    totals['total_quantity'] += int(move_line.qty_done or move_line.reserved_uom_qty or 0)
                    if move_line.product_id.weight:
                        weight = move_line.product_id.weight * (move_line.qty_done or move_line.reserved_uom_qty or 0)
                        totals['net_weight'] += weight
                        totals['gross_weight'] += weight * 1.1  # Approximate
        
        return totals

