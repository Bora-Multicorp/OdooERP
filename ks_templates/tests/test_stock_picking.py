# -*- coding: utf-8 -*-
"""Test cases for stock.picking model extensions in ks_templates"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import date
from .common import KsTemplatesCommon


class TestStockPicking(KsTemplatesCommon):
    """Test cases for stock.picking model"""

    def test_packing_list_fields(self):
        """Test that packing list fields are accessible"""
        self.stock_picking.ks_exporter_ref = 'REF001'
        self.stock_picking.ks_other_reference = 'OTHER001'
        self.stock_picking.ks_supplier_reference = 'SUP001'
        self.stock_picking.ks_reference_no_date = 'REF/2024/001'
        self.stock_picking.ks_country_of_origin = 'INDIA'
        self.stock_picking.ks_country_of_final_destination = 'USA'
        self.stock_picking.ks_terms_of_delivery_payment = 'FOB'
        self.stock_picking.ks_pre_carriage_by = 'TRUCK'
        self.stock_picking.ks_place_of_receipt_by_pre_carrier = 'MUMBAI'
        self.stock_picking.ks_vessel_flight_no = 'VESSEL001'
        self.stock_picking.ks_port_of_loading = 'MUMBAI PORT'
        self.stock_picking.ks_port_of_discharge = 'NEW YORK PORT'
        self.stock_picking.ks_final_destination = 'NEW YORK'
        self.stock_picking.ks_gross_weight = '100.500'
        self.stock_picking.ks_net_weight = '90.000'
        self.stock_picking.ks_contact_date = date.today()
        self.stock_picking.ks_contact_no = '+91-1234567890'
        self.stock_picking.ks_lut_no = 'LUT001'
        self.stock_picking.ks_lut_date = date.today()
        
        self.assertEqual(self.stock_picking.ks_exporter_ref, 'REF001')
        self.assertEqual(self.stock_picking.ks_country_of_origin, 'INDIA')
        self.assertEqual(self.stock_picking.ks_gross_weight, '100.500')
        self.assertIsNotNone(self.stock_picking.ks_contact_date)

    def test_get_invoice_info_with_sale_order(self):
        """Test get_invoice_info when picking has sale order"""
        # Create invoice from sale order
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer.id,
            'invoice_date': date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 10.0,
                'price_unit': 100.0,
            })],
        })
        invoice.action_post()
        
        # Link invoice to sale order
        self.sale_order.invoice_ids = invoice
        
        # Test get_invoice_info
        invoice_info = self.stock_picking.get_invoice_info()
        self.assertIn('invoice_no', invoice_info)
        self.assertIn('invoice_date', invoice_info)
        self.assertEqual(invoice_info['invoice_no'], invoice.name)
        self.assertEqual(invoice_info['invoice_date'], invoice.invoice_date)

    def test_get_invoice_info_without_sale_order(self):
        """Test get_invoice_info when picking has no sale order"""
        # Set origin to invoice name
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer.id,
            'invoice_date': date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 10.0,
                'price_unit': 100.0,
            })],
        })
        invoice.action_post()
        
        # Create picking without sale order but with origin
        picking = self.env['stock.picking'].create({
            'partner_id': self.customer.id,
            'company_id': self.company.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'origin': invoice.name,
        })
        
        invoice_info = picking.get_invoice_info()
        self.assertEqual(invoice_info['invoice_no'], invoice.name)

    def test_get_invoice_info_fallback(self):
        """Test get_invoice_info fallback to sale order name"""
        # Picking with sale order but no invoice
        invoice_info = self.stock_picking.get_invoice_info()
        self.assertEqual(invoice_info['invoice_no'], self.sale_order.name)
        self.assertEqual(invoice_info['invoice_date'], self.sale_order.date_order.date())

    def test_get_exporter_info(self):
        """Test get_exporter_info method"""
        exporter_info = self.stock_picking.get_exporter_info()
        
        self.assertIn('name', exporter_info)
        self.assertIn('address', exporter_info)
        self.assertIn('gst', exporter_info)
        self.assertIn('iec', exporter_info)
        
        self.assertEqual(exporter_info['name'], self.company.name)
        self.assertEqual(exporter_info['gst'], self.company.vat)
        self.assertIn('Pune', exporter_info['address'])

    def test_get_consignee_info(self):
        """Test get_consignee_info method"""
        consignee_info = self.stock_picking.get_consignee_info()
        
        self.assertIn('name', consignee_info)
        self.assertIn('address', consignee_info)
        self.assertEqual(consignee_info['name'], self.customer.name)
        self.assertIn('Vladivostok', consignee_info['address'])

    def test_get_buyer_info_with_sale_order(self):
        """Test get_buyer_info when picking has sale order"""
        buyer_info = self.stock_picking.get_buyer_info()
        
        self.assertIn('name', buyer_info)
        self.assertIn('address', buyer_info)
        self.assertEqual(buyer_info['name'], self.customer.name)

    def test_get_buyer_info_without_sale_order(self):
        """Test get_buyer_info when picking has no sale order"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.customer.id,
            'company_id': self.company.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        
        buyer_info = picking.get_buyer_info()
        self.assertEqual(buyer_info['name'], self.customer.name)

    def test_get_packing_list_lines_without_packages(self):
        """Test get_packing_list_lines without packages"""
        lines = self.stock_picking.get_packing_list_lines()
        
        self.assertIsInstance(lines, list)
        if lines:
            line = lines[0]
            self.assertIn('dimensions', line)
            self.assertIn('boxes', line)
            self.assertIn('description', line)
            self.assertIn('description_list', line)
            self.assertIn('quantity', line)
            self.assertIn('quantity_list', line)
            self.assertIn('total_quantity', line)
            self.assertIn('remarks', line)

    def test_get_packing_list_totals_without_packages(self):
        """Test get_packing_list_totals without packages"""
        totals = self.stock_picking.get_packing_list_totals()
        
        self.assertIn('total_packages', totals)
        self.assertIn('total_boxes', totals)
        self.assertIn('total_quantity', totals)
        self.assertIn('gross_weight', totals)
        self.assertIn('net_weight', totals)
        
        self.assertGreaterEqual(totals['total_quantity'], 0)
        self.assertGreaterEqual(totals['gross_weight'], 0.0)
        self.assertGreaterEqual(totals['net_weight'], 0.0)

    def test_get_packing_list_totals_with_manual_weights(self):
        """Test get_packing_list_totals with manual weight fields"""
        self.stock_picking.ks_gross_weight = '150.500'
        self.stock_picking.ks_net_weight = '140.000'
        
        # The method should still return calculated values
        totals = self.stock_picking.get_packing_list_totals()
        self.assertIsInstance(totals['gross_weight'], float)
        self.assertIsInstance(totals['net_weight'], float)

    def test_packing_list_fields_defaults(self):
        """Test default values for packing list fields"""
        picking = self.env['stock.picking'].create({
            'partner_id': self.customer.id,
            'company_id': self.company.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        
        # Test default value for country of origin
        self.assertEqual(picking.ks_country_of_origin, 'INDIA')

    def test_get_packing_list_lines_empty_picking(self):
        """Test get_packing_list_lines with empty picking"""
        empty_picking = self.env['stock.picking'].create({
            'partner_id': self.customer.id,
            'company_id': self.company.id,
            'picking_type_id': self.env.ref('stock.picking_type_out').id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
        })
        
        lines = empty_picking.get_packing_list_lines()
        self.assertIsInstance(lines, list)

