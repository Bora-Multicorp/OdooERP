# -*- coding: utf-8 -*-
"""Test cases for sale.order model extensions in ks_templates"""

from .common import KsTemplatesCommon


class TestSaleOrder(KsTemplatesCommon):
    """Test cases for sale.order model"""

    def test_ks_other_reference_field(self):
        """Test ks_other_reference field"""
        self.sale_order.ks_other_reference = 'REF001'
        self.assertEqual(self.sale_order.ks_other_reference, 'REF001')

    def test_ks_additional_terms_of_delivery_field(self):
        """Test ks_additional_terms_of_delivery field"""
        self.sale_order.ks_additional_terms_of_delivery = 'CONTRACT NO. : DNS - BORA 2024'
        self.assertEqual(self.sale_order.ks_additional_terms_of_delivery, 'CONTRACT NO. : DNS - BORA 2024')

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

    def test_get_line_description_with_part_code(self):
        """Test get_line_description displays [part_code] when part_code is set"""
        line = self.sale_order.order_line[0]
        line.product_id.default_code = 'SO_DEF_1'
        if hasattr(line.product_id, 'part_code'):
            line.product_id.part_code = 'SO_PART_1'
        elif hasattr(line.product_id.product_tmpl_id, 'part_code'):
            line.product_id.product_tmpl_id.part_code = 'SO_PART_1'

        line.name = '[SO_DEF_1] Sale Order Line Item'
        desc = self.sale_order.get_line_description(line)
        self.assertTrue(desc.startswith('[SO_PART_1]'))
        self.assertIn('Sale Order Line Item', desc)
        self.assertEqual(line.get_line_description(), desc)

    def test_get_line_description_fallback_default_code(self):
        """Test get_line_description falls back to [default_code] when part_code is absent or null"""
        line = self.sale_order.order_line[0]
        line.product_id.default_code = 'SO_DEF_2'
        if hasattr(line.product_id, 'part_code'):
            line.product_id.part_code = False
        if hasattr(line.product_id.product_tmpl_id, 'part_code'):
            line.product_id.product_tmpl_id.part_code = False

        line.name = '[SO_DEF_2] Sale Order Line Item'
        desc = self.sale_order.get_line_description(line)
        self.assertTrue(desc.startswith('[SO_DEF_2]'))
        self.assertIn('Sale Order Line Item', desc)
        self.assertEqual(line.get_line_description(), desc)

    def test_get_line_description_variant_with_template_part_code(self):
        """Test variant item displays template's part_code when variant part_code is absent/null"""
        line = self.sale_order.order_line[0]
        line.product_id.default_code = 'VAR_DEF_SO'
        if hasattr(line.product_id, 'part_code'):
            line.product_id.part_code = False
        if hasattr(line.product_id.product_tmpl_id, 'part_code'):
            line.product_id.product_tmpl_id.part_code = 'TMPL_PART_SO'

        line.name = '[VAR_DEF_SO] Variant SO Line Description'
        desc = self.sale_order.get_line_description(line)
        self.assertTrue(desc.startswith('[TMPL_PART_SO]'))
        self.assertIn('Variant SO Line Description', desc)
        self.assertEqual(line.get_line_description(), desc)

    def test_get_line_description_variant_fallback_to_variant_default_code(self):
        """Test variant item falls back to variant's default_code when neither variant nor template has part_code"""
        line = self.sale_order.order_line[0]
        line.product_id.default_code = 'VAR_DEF_SO_2'
        if hasattr(line.product_id.product_tmpl_id, 'default_code'):
            line.product_id.product_tmpl_id.default_code = 'TMPL_DEF_SO_2'
        if hasattr(line.product_id, 'part_code'):
            line.product_id.part_code = False
        if hasattr(line.product_id.product_tmpl_id, 'part_code'):
            line.product_id.product_tmpl_id.part_code = False

        line.name = '[VAR_DEF_SO_2] Variant SO Line Description'
        desc = self.sale_order.get_line_description(line)
        self.assertTrue(desc.startswith('[VAR_DEF_SO_2]'))
        self.assertIn('Variant SO Line Description', desc)
        self.assertEqual(line.get_line_description(), desc)

    def test_transfer_and_cash_handling_charges_identification_and_total_qty(self):
        """Test Transfer Charges and Cash Handling Charges detection and total quantity calculation."""
        # Regular line
        reg_line = self.sale_order.order_line[0]
        reg_line.product_uom_qty = 5.0
        self.assertFalse(reg_line.is_transfer_or_cash_handling_charge())
        self.assertFalse(self.sale_order.is_transfer_or_cash_handling_charge(reg_line))

        # Transfer charge line
        transfer_product = self.env['product.product'].create({
            'name': 'TRANSFER CHARGES',
            'default_code': 'TRANSFER-CHARGES',
            'type': 'service',
        })
        transfer_line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': transfer_product.id,
            'name': 'Transfer Charges (100 USD Flat)',
            'product_uom_qty': 1.0,
            'price_unit': 100.0,
        })
        self.assertTrue(transfer_line.is_transfer_or_cash_handling_charge())
        self.assertTrue(self.sale_order.is_transfer_or_cash_handling_charge(transfer_line))

        # Cash handling charge line
        cash_product = self.env['product.product'].create({
            'name': 'CASH HANDLING CHARGES',
            'default_code': 'CASH-HANDLING',
            'type': 'service',
        })
        cash_line = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': cash_product.id,
            'name': 'Cash Handling Charges (1.2% - AED)',
            'product_uom_qty': 1.0,
            'price_unit': 50.0,
        })
        self.assertTrue(cash_line.is_transfer_or_cash_handling_charge())
        self.assertTrue(self.sale_order.is_transfer_or_cash_handling_charge(cash_line))

        # Total qty should only count regular line (5.0), excluding the 1.0 + 1.0 charges
        self.assertEqual(self.sale_order.get_printable_total_qty(), 5.0)

        # Singular variations
        transfer_prod_singular = self.env['product.product'].create({
            'name': 'TRANSFER CHARGE',
            'default_code': 'TRANSFER-CHARGE',
            'type': 'service',
        })
        transfer_line_singular = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': transfer_prod_singular.id,
            'name': 'Transfer Charge (80 USD)',
            'product_uom_qty': 2.0,
            'price_unit': 80.0,
        })
        self.assertTrue(transfer_line_singular.is_transfer_or_cash_handling_charge())
        self.assertTrue(self.sale_order.is_transfer_or_cash_handling_charge(transfer_line_singular))

        cash_prod_singular = self.env['product.product'].create({
            'name': 'Cash Handling Charge',
            'default_code': 'CASH-HANDLING-FEE',
            'type': 'service',
        })
        cash_line_singular = self.env['sale.order.line'].create({
            'order_id': self.sale_order.id,
            'product_id': cash_prod_singular.id,
            'name': 'Cash Handling Charge (1%)',
            'product_uom_qty': 3.0,
            'price_unit': 40.0,
        })
        self.assertTrue(cash_line_singular.is_transfer_or_cash_handling_charge())
        self.assertTrue(self.sale_order.is_transfer_or_cash_handling_charge(cash_line_singular))

        # Total qty should still only count regular line (5.0)
        self.assertEqual(self.sale_order.get_printable_total_qty(), 5.0)

    def test_type_of_sale_and_sequence_generation(self):
        """Test type_of_sale selection and custom sequence generation for SO and invoice"""
        company_bora = self.env['res.company'].create({
            'name': 'BORA TECHNOVATION PRIVATE LIMITED-Energy Sector',
        })
        # Ensure sale journal exists for invoice creation in company_bora
        self.env['account.journal'].create({
            'name': 'Customer Invoices Bora',
            'type': 'sale',
            'code': 'SINV',
            'company_id': company_bora.id,
        })
        partner = self.env['res.partner'].create({
            'name': 'Customer Test Bora',
            'company_id': company_bora.id,
        })

        # Test High Seas Sale
        so_hss = self.env['sale.order'].create({
            'partner_id': partner.id,
            'company_id': company_bora.id,
            'type_of_sale': 'high_seas_sale',
        })
        self.assertEqual(so_hss.type_of_sale, 'high_seas_sale')
        self.assertTrue(so_hss.name.startswith('BTPL/HSS/'))
        self.assertTrue(so_hss.name.endswith('/001'))

        inv_vals_hss = so_hss._prepare_invoice()
        self.assertEqual(inv_vals_hss.get('type_of_sale'), 'high_seas_sale')
        inv_hss = self.env['account.move'].create(inv_vals_hss)
        self.assertEqual(inv_hss.type_of_sale, 'high_seas_sale')
        self.assertTrue(inv_hss.name.startswith('BTPL/HSS/'))
        self.assertNotIn('/PI/', inv_hss.name)

        # Test IGCR
        so_igcr = self.env['sale.order'].create({
            'partner_id': partner.id,
            'company_id': company_bora.id,
            'type_of_sale': 'igcr',
        })
        self.assertEqual(so_igcr.type_of_sale, 'igcr')
        self.assertTrue(so_igcr.name.startswith('BTPL/IGCR/'))
        self.assertTrue(so_igcr.name.endswith('/001'))

        inv_vals_igcr = so_igcr._prepare_invoice()
        inv_igcr = self.env['account.move'].create(inv_vals_igcr)
        self.assertEqual(inv_igcr.type_of_sale, 'igcr')
        self.assertTrue(inv_igcr.name.startswith('BTPL/IGCR/'))

        # Test Direct
        so_direct = self.env['sale.order'].create({
            'partner_id': partner.id,
            'company_id': company_bora.id,
            'type_of_sale': 'direct',
        })
        self.assertEqual(so_direct.type_of_sale, 'direct')
        self.assertTrue(so_direct.name.startswith('BTPL/DIRECT/'))
        self.assertTrue(so_direct.name.endswith('/001'))

        inv_vals_direct = so_direct._prepare_invoice()
        inv_direct = self.env['account.move'].create(inv_vals_direct)
        self.assertEqual(inv_direct.type_of_sale, 'direct')
        self.assertTrue(inv_direct.name.startswith('BTPL/DIRECT/'))

        # Test changing dropdown multiple times on existing draft sale order
        # Change 1: from DIRECT to HIGH SEAS SALE
        so_direct.type_of_sale = 'high_seas_sale'
        so_direct._onchange_type_of_sale()
        self.assertTrue(so_direct.name.startswith('BTPL/HSS/'), f"Expected BTPL/HSS/ but got {so_direct.name}")

        # Change 2: from HIGH SEAS SALE to IGCR via write
        so_direct.write({'type_of_sale': 'igcr'})
        self.assertTrue(so_direct.name.startswith('BTPL/IGCR/'), f"Expected BTPL/IGCR/ but got {so_direct.name}")

        # Change 3: from IGCR back to DIRECT
        so_direct.write({'type_of_sale': 'direct'})
        self.assertTrue(so_direct.name.startswith('BTPL/DIRECT/'), f"Expected BTPL/DIRECT/ but got {so_direct.name}")

        # Test changing dropdown multiple times on existing draft invoice
        inv_direct.write({'type_of_sale': 'high_seas_sale'})
        self.assertTrue(inv_direct.name.startswith('BTPL/HSS/'), f"Expected BTPL/HSS/ but got {inv_direct.name}")
        inv_direct.write({'type_of_sale': 'igcr'})
        self.assertTrue(inv_direct.name.startswith('BTPL/IGCR/'), f"Expected BTPL/IGCR/ but got {inv_direct.name}")



