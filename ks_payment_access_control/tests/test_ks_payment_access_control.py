# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
from .common import KsPaymentAccessControlCommon


class TestKsPaymentAccessControl(KsPaymentAccessControlCommon):
    """Test cases for Payment Access Control functionality"""

    def test_01_user_with_access_can_read_payment(self):
        """Test: User with payment access can read payments"""
        payment = self.env['account.payment'].with_user(self.user_with_access).create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        
        # User with access should be able to read
        payment.with_user(self.user_with_access).check_access_rights('read', raise_exception=True)
        self.assertTrue(True, "User with access can read payment")

    def test_02_user_without_access_cannot_read_payment(self):
        """Test: User without payment access cannot read payments"""
        payment = self.env['account.payment'].with_user(self.user_with_access).create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        
        with self.assertRaises(AccessError):
            payment.with_user(self.user_without_access).check_access_rights('read', raise_exception=True)

    def test_03_user_with_access_can_create_payment(self):
        """Test: User with payment access can create payments"""
        payment = self.env['account.payment'].with_user(self.user_with_access).create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        
        self.assertTrue(payment.id, "User with access can create payment")

    def test_04_user_without_access_cannot_create_payment(self):
        """Test: User without payment access cannot create payments"""
        with self.assertRaises(AccessError):
            self.env['account.payment'].with_user(self.user_without_access).create({
                'amount': 100.0,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.customer.id,
                'journal_id': self.journal.id,
                'company_id': self.company.id,
            })

    def test_05_user_with_access_can_write_payment(self):
        """Test: User with payment access can write payments"""
        payment = self.env['account.payment'].with_user(self.user_with_access).create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        
        payment.with_user(self.user_with_access).write({
            'amount': 200.0,
        })
        
        self.assertEqual(payment.amount, 200.0, "User with access can write payment")

    def test_06_user_without_access_cannot_write_payment(self):
        """Test: User without payment access cannot write payments"""
        payment = self.env['account.payment'].with_user(self.user_with_access).create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        
        with self.assertRaises(AccessError):
            payment.with_user(self.user_without_access).write({
                'amount': 200.0,
            })

    def test_07_user_with_access_can_delete_payment(self):
        """Test: User with payment access can delete payments"""
        payment = self.env['account.payment'].with_user(self.user_with_access).create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        
        payment_id = payment.id
        payment.with_user(self.user_with_access).unlink()
        
        self.assertFalse(self.env['account.payment'].browse(payment_id).exists(), 
                        "User with access can delete payment")

    def test_08_user_without_access_cannot_delete_payment(self):
        """Test: User without payment access cannot delete payments"""
        payment = self.env['account.payment'].with_user(self.user_with_access).create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        
        with self.assertRaises(AccessError):
            payment.with_user(self.user_without_access).unlink()

    def test_09_superuser_bypasses_access_control(self):
        """Test: Superuser bypasses access control"""
        payment = self.env['account.payment'].sudo().create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        
        # Superuser should be able to access
        payment.sudo().check_access_rights('read', raise_exception=True)
        self.assertTrue(True, "Superuser can access payment")

    def test_10_check_access_rule_enforced(self):
        """Test: check_access_rule is enforced for record-level access"""
        payment = self.env['account.payment'].with_user(self.user_with_access).create({
            'amount': 100.0,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'journal_id': self.journal.id,
            'company_id': self.company.id,
        })
        
        with self.assertRaises(AccessError):
            payment.with_user(self.user_without_access).check_access_rule('read')

