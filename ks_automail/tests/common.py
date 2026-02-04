# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class KsAutomailCommon(TransactionCase):
    """Common setup for Auto Mail tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Auto Mail Company',
        })
        
        # Create customer with email
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'email': 'customer@test.com',
            'customer_rank': 1,
            'company_id': cls.company.id,
        })
        
        # Create recipient partner
        cls.recipient = cls.env['res.partner'].create({
            'name': 'Email Recipient',
            'email': 'recipient@test.com',
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
            'ks_zone': 'india',
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': 10.0,
                'price_unit': 100.0,
            })],
        })
        
        # Create email templates
        cls.confirmation_template = cls.env['mail.template'].create({
            'name': 'Test Confirmation Template',
            'model_id': cls.env.ref('sale.model_sale_order').id,
            'subject': 'Order Confirmed: {{ object.name }}',
            'body_html': '<p>Your order {{ object.name }} has been confirmed.</p>',
            'email_from': '{{ object.company_id.email_formatted }}',
        })
        
        cls.packed_template = cls.env['mail.template'].create({
            'name': 'Test Packed Template',
            'model_id': cls.env.ref('sale.model_sale_order').id,
            'subject': 'Order Packed: {{ object.name }}',
            'body_html': '<p>Your order {{ object.name }} has been packed.</p>',
            'email_from': '{{ object.company_id.email_formatted }}',
        })
        
        cls.shipped_template = cls.env['mail.template'].create({
            'name': 'Test Shipped Template',
            'model_id': cls.env.ref('sale.model_sale_order').id,
            'subject': 'Order Shipped: {{ object.name }}',
            'body_html': '<p>Your order {{ object.name }} has been shipped.</p>',
            'email_from': '{{ object.company_id.email_formatted }}',
        })

