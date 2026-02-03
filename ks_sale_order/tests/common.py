# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields


class KsSaleOrderCommon(TransactionCase):
    """Common setup for Sale Order tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Sale Order Company',
        })
        
        # Create warehouse for company
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
            'company_id': cls.company.id,
        })
        
        # Create location
        cls.location = cls.warehouse.lot_stock_id
        
        # Create customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'customer_rank': 1,
            'company_id': cls.company.id,
        })
        
        # Create product with stock
        cls.product_with_stock = cls.env['product.product'].create({
            'name': 'Product With Stock',
            'type': 'product',
            'sale_ok': True,
            'list_price': 100.0,
        })
        
        # Create product without stock
        cls.product_no_stock = cls.env['product.product'].create({
            'name': 'Product No Stock',
            'type': 'product',
            'sale_ok': True,
            'list_price': 100.0,
        })
        
        # Create procurement team users
        cls.procurement_user_1 = cls.env['res.users'].create({
            'name': 'Procurement User 1',
            'login': 'procurement_user_1',
            'email': 'procurement1@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
        })
        
        cls.procurement_user_2 = cls.env['res.users'].create({
            'name': 'Procurement User 2',
            'login': 'procurement_user_2',
            'email': 'procurement2@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
        })
        
        # Set procurement team for company
        cls.company.ks_sale_procurement_team_user_ids = [(6, 0, [cls.procurement_user_1.id, cls.procurement_user_2.id])]
        
        # Add stock to product_with_stock
        cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': cls.product_with_stock.id,
            'location_id': cls.location.id,
            'inventory_quantity': 100.0,
        })

    def _create_sale_order(self, user=None, company=None):
        """Helper method to create a sale order"""
        if user is None:
            user = self.env.user
        if company is None:
            company = self.company
        
        return self.env['sale.order'].with_user(user).with_company(company).create({
            'partner_id': self.customer.id,
            'company_id': company.id,
            'warehouse_id': self.warehouse.id,
            'order_line': [(0, 0, {
                'product_id': self.product_with_stock.id,
                'product_uom_qty': 10.0,
                'price_unit': 100.0,
            })],
        })

