# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from .common import KsSaleAdvancePaymentCommon


class TestKsSaleAdvancePayment(KsSaleAdvancePaymentCommon):
    """Test cases for Sale Advance Payment functionality"""

    def test_01_create_advance_payment_wizard(self):
        """Test: Create advance payment wizard"""
        wizard = self.env['sale.advance.payment'].create({
            'sale_order_id': self.sale_order.id,
            'amount': 500.0,
            'journal_id': self.journal.id,
            'payment_date': '2024-01-01',
        })
        
        self.assertEqual(wizard.sale_order_id, self.sale_order)
        self.assertEqual(wizard.amount, 500.0)
        self.assertEqual(wizard.currency_id, self.sale_order.currency_id)

    def test_02_wizard_computes_currency_from_sale_order(self):
        """Test: Wizard computes currency from sale order"""
        wizard = self.env['sale.advance.payment'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        self.assertEqual(wizard.currency_id, self.sale_order.currency_id)

    def test_03_wizard_computes_company_from_sale_order(self):
        """Test: Wizard computes company from sale order"""
        wizard = self.env['sale.advance.payment'].create({
            'sale_order_id': self.sale_order.id,
        })
        
        self.assertEqual(wizard.company_id, self.sale_order.company_id)

    def test_04_create_advance_payment_creates_payment_record(self):
        """Test: Creating advance payment creates account.payment record"""
        wizard = self.env['sale.advance.payment'].create({
            'sale_order_id': self.sale_order.id,
            'amount': 500.0,
            'journal_id': self.journal.id,
            'payment_date': '2024-01-01',
        })
        
        # Get payment method
        if self.journal.inbound_payment_method_line_ids:
            wizard.payment_method_line_id = self.journal.inbound_payment_method_line_ids[0]
        
        result = wizard.action_create_payment()
        
        # Check that payment was created
        payment = self.env['account.payment'].browse(result['res_id'])
        self.assertEqual(payment.amount, 500.0)
        self.assertEqual(payment.partner_id, self.customer)
        self.assertEqual(payment.ks_sale_order_id, self.sale_order)

    def test_05_advance_payment_linked_to_sale_order(self):
        """Test: Advance payment is linked to sale order"""
        wizard = self.env['sale.advance.payment'].create({
            'sale_order_id': self.sale_order.id,
            'amount': 500.0,
            'journal_id': self.journal.id,
            'payment_date': '2024-01-01',
        })
        
        if self.journal.inbound_payment_method_line_ids:
            wizard.payment_method_line_id = self.journal.inbound_payment_method_line_ids[0]
        
        wizard.action_create_payment()
        
        # Check sale order has payment linked
        self.assertGreater(len(self.sale_order.ks_advance_payment_ids), 0)

    def test_06_compute_advance_payment_amount(self):
        """Test: Compute advance payment amount on sale order"""
        # Create payment
        payment = self.env['account.payment'].create({
            'amount': 500.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
            'ks_sale_order_id': self.sale_order.id,
        })
        payment.action_post()
        
        # Check computed amount
        self.sale_order._compute_ks_advance_payment_amount()
        self.assertEqual(self.sale_order.ks_advance_payment_amount, 500.0)

    def test_07_compute_advance_payment_balance(self):
        """Test: Compute balance due after advance payments"""
        # Create payment
        payment = self.env['account.payment'].create({
            'amount': 500.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
            'ks_sale_order_id': self.sale_order.id,
        })
        payment.action_post()
        
        # Check balance
        self.sale_order._compute_ks_advance_payment_amount()
        expected_balance = self.sale_order.amount_total - 500.0
        self.assertEqual(self.sale_order.ks_advance_payment_balance, expected_balance)

    def test_08_only_posted_payments_counted(self):
        """Test: Only posted payments are counted in advance payment amount"""
        # Create draft payment
        payment = self.env['account.payment'].create({
            'amount': 500.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
            'ks_sale_order_id': self.sale_order.id,
            'state': 'draft',
        })
        
        self.sale_order._compute_ks_advance_payment_amount()
        self.assertEqual(self.sale_order.ks_advance_payment_amount, 0.0, "Draft payments should not be counted")

    def test_09_negative_amount_raises_error(self):
        """Test: Negative payment amount raises error"""
        wizard = self.env['sale.advance.payment'].create({
            'sale_order_id': self.sale_order.id,
            'amount': -100.0,
            'journal_id': self.journal.id,
        })
        
        if self.journal.inbound_payment_method_line_ids:
            wizard.payment_method_line_id = self.journal.inbound_payment_method_line_ids[0]
        
        with self.assertRaises(UserError):
            wizard.action_create_payment()

    def test_10_action_view_advance_payments(self):
        """Test: Action to view advance payments"""
        # Create payment
        payment = self.env['account.payment'].create({
            'amount': 500.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
            'ks_sale_order_id': self.sale_order.id,
        })
        payment.action_post()
        
        action = self.sale_order.action_view_advance_payments()
        
        self.assertEqual(action['res_model'], 'account.payment')
        self.assertIn(payment.id, action.get('domain', [('id', 'in', [payment.id])])[0][2] if isinstance(action.get('domain'), list) else [])

