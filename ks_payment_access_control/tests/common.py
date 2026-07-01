# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class KsPaymentAccessControlCommon(TransactionCase):
    """Common setup for Payment Access Control tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Get payment access group
        cls.payment_access_group = cls.env.ref('ks_payment_access_control.group_ks_payment_access')
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Payment Access Company',
        })
        
        # Create user with payment access
        cls.user_with_access = cls.env['res.users'].create({
            'name': 'User With Payment Access',
            'login': 'user_with_access',
            'email': 'with_access@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.payment_access_group.id)],
        })
        
        # Create user without payment access
        cls.user_without_access = cls.env['res.users'].create({
            'name': 'User Without Payment Access',
            'login': 'user_without_access',
            'email': 'without_access@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
        })
        
        # Create customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'customer_rank': 1,
            'company_id': cls.company.id,
        })
        
        # Create payment journal
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Bank Journal',
            'type': 'bank',
            'code': 'TEST',
            'company_id': cls.company.id,
        })

