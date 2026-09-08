# -*- coding: utf-8 -*-
"""Test cases for purchase.order model extensions in ks_templates"""

from .common import KsTemplatesCommon


class TestPurchaseOrder(KsTemplatesCommon):
    """Test cases for purchase.order model"""

    def test_get_amount_in_words_aed_integer(self):
        """Test get_amount_in_words_aed with integer amount"""
        result = self.purchase_order.get_amount_in_words_aed(100.0)
        self.assertIsInstance(result, str)
        self.assertIn('UAE Dirham', result)
        self.assertIn('Only', result)

    def test_get_amount_in_words_aed_with_fractional(self):
        """Test get_amount_in_words_aed with fractional amount"""
        result = self.purchase_order.get_amount_in_words_aed(100.50)
        self.assertIsInstance(result, str)
        self.assertIn('UAE Dirham', result)
        self.assertIn('fils', result.lower())
        self.assertIn('Only', result)

    def test_get_amount_in_words_inr_integer(self):
        """Test get_amount_in_words_inr with integer amount"""
        result = self.purchase_order.get_amount_in_words_inr(100.0)
        self.assertIsInstance(result, str)
        self.assertIn('INR', result)
        self.assertIn('Only', result)

    def test_get_amount_in_words_inr_with_fractional(self):
        """Test get_amount_in_words_inr with fractional amount"""
        result = self.purchase_order.get_amount_in_words_inr(100.50)
        self.assertIsInstance(result, str)
        self.assertIn('INR', result)
        self.assertIn('Paise', result)
        self.assertIn('Only', result)

    def test_format_number(self):
        """Test format_number method"""
        result = self.purchase_order.format_number(1234.567, digits=2)
        self.assertIsInstance(result, str)

    def test_format_currency_amount(self):
        """Test format_currency_amount method"""
        result = self.purchase_order.format_currency_amount(1000.0)
        self.assertIsInstance(result, str)

    def test_format_currency_amount_with_currency(self):
        """Test format_currency_amount with specific currency"""
        result = self.purchase_order.format_currency_amount(1000.0, currency=self.currency_inr)
        self.assertIsInstance(result, str)

    def test_get_discount_amount_no_discount(self):
        """Test get_discount_amount with no discount"""
        discount = self.purchase_order.get_discount_amount()
        self.assertIsInstance(discount, float)
        self.assertEqual(discount, 0.0)

    def test_get_discount_amount_with_discount(self):
        """Test get_discount_amount with discount"""
        # Add discount to order line
        self.purchase_order.order_line[0].discount = 10.0
        discount = self.purchase_order.get_discount_amount()
        self.assertIsInstance(discount, float)
        self.assertGreater(discount, 0.0)

    def test_get_cgst_sgst_info(self):
        """Test get_cgst_sgst_info method"""
        cgst_sgst_info = self.purchase_order.get_cgst_sgst_info()
        
        self.assertIn('cgst_rate', cgst_sgst_info)
        self.assertIn('cgst_amount', cgst_sgst_info)
        self.assertIn('sgst_rate', cgst_sgst_info)
        self.assertIn('sgst_amount', cgst_sgst_info)
        
        # CGST and SGST should be equal (50% each)
        self.assertEqual(cgst_sgst_info['cgst_amount'], cgst_sgst_info['sgst_amount'])

    def test_get_tds_info(self):
        """Test get_tds_info method"""
        tds_info = self.purchase_order.get_tds_info()
        
        self.assertIn('tds_name', tds_info)
        self.assertIn('tds_amount', tds_info)
        self.assertIsInstance(tds_info['tds_name'], str)
        self.assertIsInstance(tds_info['tds_amount'], float)
        self.assertGreaterEqual(tds_info['tds_amount'], 0.0)

    def test_get_line_hsn_code(self):
        """Test get_line_hsn_code method"""
        line = self.purchase_order.order_line[0]
        hsn_code = self.purchase_order.get_line_hsn_code(line)
        self.assertIsInstance(hsn_code, str)

    def test_get_line_hsn_code_with_hsn(self):
        """Test get_line_hsn_code when product has HSN code"""
        # Try to set HSN code if field exists
        if hasattr(self.product.product_tmpl_id, 'l10n_in_hsn_code'):
            self.product.product_tmpl_id.l10n_in_hsn_code = '12345678'
            line = self.purchase_order.order_line[0]
            hsn_code = self.purchase_order.get_line_hsn_code(line)
            # Should return HSN code if field exists and is set
            if hsn_code:
                self.assertIsInstance(hsn_code, str)

    def test_get_bill_to_company_name(self):
        """Test get_bill_to_company_name method"""
        res = self.purchase_order.get_bill_to_company_name()
        self.assertIsInstance(res, str)
        self.assertTrue(len(res) > 0)

    def test_get_ship_to_company_name(self):
        """Test get_ship_to_company_name method"""
        res = self.purchase_order.get_ship_to_company_name()
        self.assertIsInstance(res, str)
        self.assertTrue(len(res) > 0)


