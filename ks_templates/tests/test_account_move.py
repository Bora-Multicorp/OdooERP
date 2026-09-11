# -*- coding: utf-8 -*-
"""Test cases for account.move model extensions in ks_templates"""

from datetime import date
from .common import KsTemplatesCommon


class TestAccountMove(KsTemplatesCommon):
    """Test cases for account.move model"""

    def setUp(self):
        super().setUp()
        # Create invoice
        self.invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer.id,
            'company_id': self.company.id,
            'invoice_date': date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 10.0,
                'price_unit': 100.0,
            })],
        })

    def test_invoice_fields(self):
        """Test invoice extension fields"""
        self.invoice.ks_delivery_note = 'DN001'
        self.invoice.ks_supplier_reference = 'SUP001'
        self.invoice.ks_reference_no_date = 'REF/2024/001'
        self.invoice.ks_despatch_document_no = 'DDN001'
        self.invoice.ks_delivery_note_date = date.today()
        self.invoice.ks_despatched_through = 'BY SEA'
        self.invoice.ks_vessel_flight_no = 'VESSEL001'
        self.invoice.ks_place_of_receipt_by_shipper = 'MUMBAI'
        self.invoice.ks_city_port_of_loading = 'MUMBAI PORT'
        self.invoice.ks_city_port_of_discharge = 'NEW YORK PORT'
        
        self.assertEqual(self.invoice.ks_delivery_note, 'DN001')
        self.assertEqual(self.invoice.ks_supplier_reference, 'SUP001')
        self.assertEqual(self.invoice.ks_vessel_flight_no, 'VESSEL001')

    def test_get_amount_in_words_aed_integer(self):
        """Test get_amount_in_words_aed with integer amount"""
        result = self.invoice.get_amount_in_words_aed(100.0)
        self.assertIsInstance(result, str)
        self.assertIn('UAE Dirham', result)
        self.assertIn('Only', result)

    def test_get_amount_in_words_aed_with_fractional(self):
        """Test get_amount_in_words_aed with fractional amount"""
        result = self.invoice.get_amount_in_words_aed(100.50)
        self.assertIsInstance(result, str)
        self.assertIn('UAE Dirham', result)
        self.assertIn('fils', result.lower())
        self.assertIn('Only', result)

    def test_get_amount_in_words_inr_integer(self):
        """Test get_amount_in_words_inr with integer amount"""
        result = self.invoice.get_amount_in_words_inr(100.0)
        self.assertIsInstance(result, str)
        self.assertIn('INR', result)
        self.assertIn('Only', result)

    def test_get_amount_in_words_inr_with_fractional(self):
        """Test get_amount_in_words_inr with fractional amount"""
        result = self.invoice.get_amount_in_words_inr(100.50)
        self.assertIsInstance(result, str)
        self.assertIn('INR', result)
        self.assertIn('Paise', result)
        self.assertIn('Only', result)

    def test_format_number(self):
        """Test format_number method"""
        result = self.invoice.format_number(1234.567, digits=2)
        self.assertIsInstance(result, str)

    def test_is_igst_tax(self):
        """Test _is_igst_tax method"""
        # Create a tax
        tax = self.env['account.tax'].create({
            'name': 'Test Tax',
            'amount': 18.0,
            'type_tax_use': 'sale',
        })
        
        # Test with tax that doesn't have l10n_in_tax_type
        result = self.invoice._is_igst_tax(tax)
        self.assertFalse(result)

    def test_get_igst_tax_info(self):
        """Test get_igst_tax_info method"""
        tax_info = self.invoice.get_igst_tax_info()
        self.assertIsInstance(tax_info, dict)

    def test_get_igst_tax_details(self):
        """Test get_igst_tax_details method"""
        tax_details = self.invoice.get_igst_tax_details()
        
        self.assertIn('rate', tax_details)
        self.assertIn('amount', tax_details)
        self.assertIsInstance(tax_details['rate'], float)
        self.assertIsInstance(tax_details['amount'], float)
        self.assertGreaterEqual(tax_details['rate'], 0.0)
        self.assertGreaterEqual(tax_details['amount'], 0.0)

    def test_get_sale_order_info(self):
        """Test get_sale_order_info method"""
        # Link invoice to sale order
        self.invoice.invoice_line_ids[0].sale_line_ids = self.sale_order.order_line[0]
        
        sale_order = self.invoice.get_sale_order_info()
        # Should return sale order or False
        self.assertTrue(sale_order == self.sale_order or sale_order is False)

    def test_get_sale_order_info_no_sale_order(self):
        """Test get_sale_order_info when invoice has no sale order"""
        sale_order = self.invoice.get_sale_order_info()
        self.assertFalse(sale_order)

    def test_get_line_hsn_code(self):
        """Test get_line_hsn_code method"""
        line = self.invoice.invoice_line_ids[0]
        hsn_code = self.invoice.get_line_hsn_code(line)
        self.assertIsInstance(hsn_code, str)

    def test_get_company_bank_info(self):
        """Test get_company_bank_info method"""
        bank_info = self.invoice.get_company_bank_info()
        
        self.assertIn('ad_code', bank_info)
        self.assertIn('swift_code', bank_info)
        self.assertIn('branch', bank_info)
        self.assertIn('bank_name', bank_info)
        self.assertIn('acc_number', bank_info)
        self.assertIn('ifsc_code', bank_info)
        self.assertIn('city', bank_info)
        
        # All should be strings
        for key, value in bank_info.items():
            self.assertIsInstance(value, str)

    def test_get_company_iban(self):
        """Test get_company_iban method"""
        iban = self.invoice.get_company_iban()
        self.assertIsInstance(iban, str)

    def test_get_payment_bank_info(self):
        """Test get_payment_bank_info method"""
        bank_info = self.invoice.get_payment_bank_info()
        
        self.assertIn('ad_code', bank_info)
        self.assertIn('bank_name', bank_info)
        self.assertIn('acc_number', bank_info)
        self.assertIn('ifsc_code', bank_info)
        self.assertIn('branch', bank_info)
        self.assertIn('swift_code', bank_info)
        self.assertIn('city', bank_info)
        self.assertIn('has_payment', bank_info)
        
        # has_payment should be boolean
        self.assertIsInstance(bank_info['has_payment'], bool)
        
        # All other values should be strings
        for key, value in bank_info.items():
            if key != 'has_payment':
                self.assertIsInstance(value, str)

    def test_get_payment_bank_info_no_payment(self):
        """Test get_payment_bank_info when invoice has no payment"""
        bank_info = self.invoice.get_payment_bank_info()
        self.assertFalse(bank_info['has_payment'])

    def test_commercial_invoice_visibility_non_indian_company(self):
        """Rule 1: Non-Indian company => always show Commercial Invoice option."""
        country_ae = self.env.ref('base.ae', raise_if_not_found=False) or self.env['res.country'].search([('code', '=', 'AE')], limit=1)
        foreign_company = self.env['res.company'].create({
            'name': 'Dubai Company',
            'country_id': country_ae.id if country_ae else False,
        })
        inv = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.supplier.id,  # Indian customer
            'company_id': foreign_company.id,
        })
        self.assertFalse(inv.ks_is_company_indian)
        self.assertTrue(inv.ks_show_commercial_invoice)

    def test_commercial_invoice_visibility_indian_company_indian_customer(self):
        """Rule 2: Indian company + Indian customer => hide Commercial Invoice option."""
        inv = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.supplier.id,  # Indian customer
            'company_id': self.company.id,   # Indian company
        })
        self.assertTrue(inv.ks_is_company_indian)
        self.assertTrue(inv.ks_is_customer_indian)
        self.assertFalse(inv.ks_show_commercial_invoice)

    def test_commercial_invoice_visibility_indian_company_non_indian_customer(self):
        """Rule 3: Indian company + Non-Indian customer => show Commercial Invoice option."""
        inv = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.customer.id,  # Russian/Non-Indian customer
            'company_id': self.company.id,   # Indian company
        })
        self.assertTrue(inv.ks_is_company_indian)
        self.assertFalse(inv.ks_is_customer_indian)
        self.assertTrue(inv.ks_show_commercial_invoice)


