# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
import base64


class KsDocCommon(TransactionCase):
    """Common setup for Sale Document tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Document Company',
        })
        
        # Create customer with email
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
            'customer_rank': 1,
            'company_id': cls.company.id,
        })
        
        # Create product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'service',
            'sale_ok': True,
            'list_price': 100.0,
        })
        
        # Create sale order
        cls.sale_order = cls.env['sale.order'].with_company(cls.company).create({
            'partner_id': cls.customer.id,
            'company_id': cls.company.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 10.0,
                'price_unit': 100.0,
            })],
        })
        
        # Create test file content
        cls.test_file_content = base64.b64encode(b'Test document content')

