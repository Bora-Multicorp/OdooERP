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

    def test_get_line_description_with_part_code(self):
        """Test get_line_description displays [part_code] when part_code is set"""
        line = self.invoice.invoice_line_ids[0]
        line.product_id.default_code = 'INV_DEF_1'
        if hasattr(line.product_id, 'part_code'):
            line.product_id.part_code = 'INV_PART_1'
        elif hasattr(line.product_id.product_tmpl_id, 'part_code'):
            line.product_id.product_tmpl_id.part_code = 'INV_PART_1'

        line.name = '[INV_DEF_1] Invoice Line Description'
        desc = self.invoice.get_line_description(line)
        self.assertTrue(desc.startswith('[INV_PART_1]'))
        self.assertIn('Invoice Line Description', desc)
        self.assertEqual(line.get_line_description(), desc)

    def test_get_line_description_fallback_default_code(self):
        """Test get_line_description falls back to [default_code] when part_code is absent or null"""
        line = self.invoice.invoice_line_ids[0]
        line.product_id.default_code = 'INV_DEF_2'
        if hasattr(line.product_id, 'part_code'):
            line.product_id.part_code = False
        if hasattr(line.product_id.product_tmpl_id, 'part_code'):
            line.product_id.product_tmpl_id.part_code = False

        line.name = '[INV_DEF_2] Invoice Line Description'
        desc = self.invoice.get_line_description(line)
        self.assertTrue(desc.startswith('[INV_DEF_2]'))
        self.assertIn('Invoice Line Description', desc)
        self.assertEqual(line.get_line_description(), desc)

    def test_get_line_description_variant_with_template_part_code(self):
        """Test variant item displays template's part_code when variant part_code is absent/null"""
        line = self.invoice.invoice_line_ids[0]
        line.product_id.default_code = 'VAR_DEF_INV'
        if hasattr(line.product_id, 'part_code'):
            line.product_id.part_code = False
        if hasattr(line.product_id.product_tmpl_id, 'part_code'):
            line.product_id.product_tmpl_id.part_code = 'TMPL_PART_INV'

        line.name = '[VAR_DEF_INV] Variant Invoice Line Description'
        desc = self.invoice.get_line_description(line)
        self.assertTrue(desc.startswith('[TMPL_PART_INV]'))
        self.assertIn('Variant Invoice Line Description', desc)
        self.assertEqual(line.get_line_description(), desc)

    def test_get_line_description_variant_fallback_to_variant_default_code(self):
        """Test variant item falls back to variant's default_code when neither variant nor template has part_code"""
        line = self.invoice.invoice_line_ids[0]
        line.product_id.default_code = 'VAR_DEF_INV_2'
        if hasattr(line.product_id.product_tmpl_id, 'default_code'):
            line.product_id.product_tmpl_id.default_code = 'TMPL_DEF_INV_2'
        if hasattr(line.product_id, 'part_code'):
            line.product_id.part_code = False
        if hasattr(line.product_id.product_tmpl_id, 'part_code'):
            line.product_id.product_tmpl_id.part_code = False

        line.name = '[VAR_DEF_INV_2] Variant Invoice Line Description'
        desc = self.invoice.get_line_description(line)
        self.assertTrue(desc.startswith('[VAR_DEF_INV_2]'))
        self.assertIn('Variant Invoice Line Description', desc)
        self.assertEqual(line.get_line_description(), desc)

    def test_is_dubai_or_hk_customer(self):
        """Test is_dubai_or_hk_customer with Dubai, HK, and other customers"""
        country_ae = self.env.ref('base.ae', raise_if_not_found=False) or self.env['res.country'].search([('code', '=', 'AE')], limit=1)
        country_hk = self.env.ref('base.hk', raise_if_not_found=False) or self.env['res.country'].search([('code', '=', 'HK')], limit=1)

        # 1. Dubai customer
        dubai_partner = self.env['res.partner'].create({
            'name': 'Dubai Customer',
            'country_id': country_ae.id if country_ae else False,
            'city': 'Dubai',
        })
        self.invoice.partner_id = dubai_partner
        self.assertTrue(self.invoice.is_dubai_or_hk_customer())

        # 2. Hong Kong customer
        hk_partner = self.env['res.partner'].create({
            'name': 'Hong Kong Customer',
            'country_id': country_hk.id if country_hk else False,
            'city': 'Hong Kong',
        })
        self.invoice.partner_id = hk_partner
        self.assertTrue(self.invoice.is_dubai_or_hk_customer())

        # 3. Russian/Other customer
        self.invoice.partner_id = self.customer
        self.assertFalse(self.invoice.is_dubai_or_hk_customer())

    def test_get_aed_conversion_info(self):
        """Test get_aed_conversion_info calculation, rate formatting, and words"""
        country_ae = self.env.ref('base.ae', raise_if_not_found=False) or self.env['res.country'].search([('code', '=', 'AE')], limit=1)
        usd_currency = self.env.ref('base.USD', raise_if_not_found=False) or self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

        dubai_partner = self.env['res.partner'].create({
            'name': 'Dubai Customer',
            'country_id': country_ae.id if country_ae else False,
            'city': 'Dubai',
        })
        self.invoice.partner_id = dubai_partner
        if usd_currency:
            self.invoice.currency_id = usd_currency

        # Set line amount: 9,250.00
        self.invoice.invoice_line_ids[0].quantity = 1.0
        self.invoice.invoice_line_ids[0].price_unit = 9250.00
        # Set manual rate = 3.674
        self.invoice.rate = 3.674

        aed_info = self.invoice.get_aed_conversion_info()
        self.assertEqual(aed_info['rate'], 3.674)
        self.assertEqual(aed_info['rate_formatted'], '3.674')
        self.assertAlmostEqual(aed_info['aed_amount'], 33984.50, places=2)
        self.assertIn('UAE Dirham', aed_info['aed_amount_words'])
        self.assertIn('fils', aed_info['aed_amount_words'].lower())
        self.assertIn('Only', aed_info['aed_amount_words'])

    def test_transfer_and_cash_handling_charges_identification_and_total_qty(self):
        """Test Transfer Charges and Cash Handling Charges detection and total quantity calculation on account.move."""
        reg_line = self.invoice.invoice_line_ids[0]
        reg_line.quantity = 10.0
        self.assertFalse(reg_line.is_transfer_or_cash_handling_charge())
        self.assertFalse(self.invoice.is_transfer_or_cash_handling_charge(reg_line))

        # Transfer charge line
        transfer_product = self.env['product.product'].create({
            'name': 'TRANSFER CHARGES',
            'default_code': 'TRANSFER-CHARGES',
            'type': 'service',
        })
        transfer_line = self.env['account.move.line'].create({
            'move_id': self.invoice.id,
            'product_id': transfer_product.id,
            'name': 'Transfer Charges (100 USD Flat)',
            'quantity': 1.0,
            'price_unit': 100.0,
        })
        self.assertTrue(transfer_line.is_transfer_or_cash_handling_charge())
        self.assertTrue(self.invoice.is_transfer_or_cash_handling_charge(transfer_line))

        # Cash handling charge line
        cash_product = self.env['product.product'].create({
            'name': 'CASH HANDLING CHARGES',
            'default_code': 'CASH-HANDLING',
            'type': 'service',
        })
        cash_line = self.env['account.move.line'].create({
            'move_id': self.invoice.id,
            'product_id': cash_product.id,
            'name': 'Cash Handling Charges (1.2% - AED)',
            'quantity': 1.0,
            'price_unit': 50.0,
        })
        self.assertTrue(cash_line.is_transfer_or_cash_handling_charge())
        self.assertTrue(self.invoice.is_transfer_or_cash_handling_charge(cash_line))

        # Total qty should only count regular line (10.0), excluding the 1.0 + 1.0 charges
        self.assertEqual(self.invoice.get_printable_total_qty(), 10.0)

        # Singular variations
        transfer_prod_singular = self.env['product.product'].create({
            'name': 'TRANSFER CHARGE',
            'default_code': 'TRANSFER-CHARGE',
            'type': 'service',
        })
        transfer_line_singular = self.env['account.move.line'].create({
            'move_id': self.invoice.id,
            'product_id': transfer_prod_singular.id,
            'name': 'Transfer Charge (80 USD)',
            'quantity': 2.0,
            'price_unit': 80.0,
        })
        self.assertTrue(transfer_line_singular.is_transfer_or_cash_handling_charge())
        self.assertTrue(self.invoice.is_transfer_or_cash_handling_charge(transfer_line_singular))

        cash_prod_singular = self.env['product.product'].create({
            'name': 'Cash Handling Charge',
            'default_code': 'CASH-HANDLING-FEE',
            'type': 'service',
        })
        cash_line_singular = self.env['account.move.line'].create({
            'move_id': self.invoice.id,
            'product_id': cash_prod_singular.id,
            'name': 'Cash Handling Charge (1%)',
            'quantity': 3.0,
            'price_unit': 40.0,
        })
        self.assertTrue(cash_line_singular.is_transfer_or_cash_handling_charge())
        self.assertTrue(self.invoice.is_transfer_or_cash_handling_charge(cash_line_singular))

        # Total qty should still only count regular line (10.0)
        self.assertEqual(self.invoice.get_printable_total_qty(), 10.0)


