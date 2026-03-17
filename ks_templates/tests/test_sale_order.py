# -*- coding: utf-8 -*-
"""Test cases for sale.order model extensions in ks_templates"""

from .common import KsTemplatesCommon


class TestSaleOrder(KsTemplatesCommon):
    """Test cases for sale.order model"""

    def test_ks_other_reference_field(self):
        """Test ks_other_reference field"""
        self.sale_order.ks_other_reference = 'REF001'
        self.assertEqual(self.sale_order.ks_other_reference, 'REF001')

    def test_ks_despatched_through_field(self):
        """Test ks_despatched_through field"""
        self.sale_order.ks_despatched_through = 'BY SEA'
        self.assertEqual(self.sale_order.ks_despatched_through, 'BY SEA')

    def test_ks_city_port_of_discharge_field(self):
        """Test ks_city_port_of_discharge field"""
        self.sale_order.ks_city_port_of_discharge = 'NEW YORK PORT'
        self.assertEqual(self.sale_order.ks_city_port_of_discharge, 'NEW YORK PORT')

    def test_get_amount_in_words_aed_integer(self):
        """Test get_amount_in_words_aed with integer amount"""
        result = self.sale_order.get_amount_in_words_aed(100.0)
        self.assertIsInstance(result, str)
        self.assertIn('UAE Dirham', result)
        self.assertIn('Only', result)

    def test_get_amount_in_words_aed_with_fractional(self):
        """Test get_amount_in_words_aed with fractional amount"""
        result = self.sale_order.get_amount_in_words_aed(100.50)
        self.assertIsInstance(result, str)
        self.assertIn('UAE Dirham', result)
        self.assertIn('fils', result.lower())
        self.assertIn('Only', result)

    def test_get_amount_in_words_aed_zero(self):
        """Test get_amount_in_words_aed with zero amount"""
        result = self.sale_order.get_amount_in_words_aed(0.0)
        self.assertIsInstance(result, str)
        self.assertIn('UAE Dirham', result)

    def test_format_number(self):
        """Test format_number method"""
        result = self.sale_order.format_number(1234.567, digits=2)
        self.assertIsInstance(result, str)

    def test_format_currency_amount(self):
        """Test format_currency_amount method"""
        result = self.sale_order.format_currency_amount(1000.0)
        self.assertIsInstance(result, str)

    def test_format_currency_amount_with_currency(self):
        """Test format_currency_amount with specific currency"""
        result = self.sale_order.format_currency_amount(1000.0, currency=self.currency_aed)
        self.assertIsInstance(result, str)

    def test_format_currency_with_symbol(self):
        """Test format_currency_with_symbol method"""
        result = self.sale_order.format_currency_with_symbol(1000.0)
        self.assertIsInstance(result, str)

    def test_get_company_bank_info(self):
        """Test get_company_bank_info method"""
        bank_info = self.sale_order.get_company_bank_info()
        
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
        iban = self.sale_order.get_company_iban()
        self.assertIsInstance(iban, str)

    def test_get_company_iban_no_bank(self):
        """Test get_company_iban when company has no bank"""
        # Create sale order with company without bank
        company_no_bank = self.env['res.company'].create({
            'name': 'Company No Bank',
        })
        sale_order = self.env['sale.order'].with_company(company_no_bank).create({
            'partner_id': self.customer.id,
            'company_id': company_no_bank.id,
        })
        
        iban = sale_order.get_company_iban()
        self.assertEqual(iban, '')

