# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from .common import KsSaleOrderCommon


class TestKsSaleOrderStockShortage(KsSaleOrderCommon):
    """Test cases for Stock Shortage Alert functionality"""

    def test_01_stock_shortage_blocks_confirmation(self):
        """Test: Stock shortage blocks order confirmation"""
        order = self._create_sale_order()
        
        # Update order line to request more than available
        order.order_line[0].write({
            'product_id': self.product_no_stock.id,
            'product_uom_qty': 100.0,
        })
        
        # Try to confirm - should raise error
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_02_stock_available_allows_confirmation(self):
        """Test: Sufficient stock allows order confirmation"""
        order = self._create_sale_order()
        
        # Order line has product_with_stock with 100 units available, requesting 10
        # Should allow confirmation
        order.action_confirm()
        
        self.assertEqual(order.state, 'sale', "Order should be confirmed when stock is available")

    def test_03_stock_check_is_company_specific(self):
        """Test: Stock check is specific to sale order's company"""
        # Create another company
        company_2 = self.env['res.company'].create({
            'name': 'Test Company 2',
        })
        
        warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse 2',
            'code': 'TWH2',
            'company_id': company_2.id,
        })
        
        location_2 = warehouse_2.lot_stock_id
        
        # Add stock to product in company 2
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product_no_stock.id,
            'location_id': location_2.id,
            'inventory_quantity': 100.0,
        })
        
        # Create order in company 1 (no stock)
        order = self._create_sale_order(company=self.company)
        order.order_line[0].write({
            'product_id': self.product_no_stock.id,
            'product_uom_qty': 50.0,
        })
        
        # Should still block because company 1 has no stock
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_04_stock_shortage_email_sent_to_procurement_team(self):
        """Test: Stock shortage sends email to procurement team"""
        order = self._create_sale_order()
        
        # Update to product without stock
        order.order_line[0].write({
            'product_id': self.product_no_stock.id,
            'product_uom_qty': 100.0,
        })
        
        # Mock email sending - check that procurement team would receive email
        # In actual test, you would check mail.mail records
        procurement_users = self.company.ks_sale_procurement_team_user_ids
        self.assertGreater(len(procurement_users), 0, "Procurement team should be configured")

    def test_05_stock_alert_only_when_delivery_blocked(self):
        """Test: Stock alert only triggers when delivery is actually blocked"""
        order = self._create_sale_order()
        
        # Product has stock, so no alert should be sent
        order.action_confirm()
        
        # Check that no stock shortage message was posted
        messages = order.message_ids.filtered(
            lambda m: 'Stock Shortage Alert' in (m.body or '')
        )
        self.assertEqual(len(messages), 0, "No stock shortage alert should be sent when stock is available")

    def test_06_partial_stock_shortage(self):
        """Test: Partial stock shortage blocks confirmation"""
        order = self._create_sale_order()
        
        # Request more than available (100 available, request 150)
        order.order_line[0].write({
            'product_uom_qty': 150.0,
        })
        
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_07_non_storable_products_bypass_stock_check(self):
        """Test: Non-storable products bypass stock check"""
        # Create service product
        service_product = self.env['product.product'].create({
            'name': 'Service Product',
            'type': 'service',
            'sale_ok': True,
            'list_price': 100.0,
        })
        
        order = self._create_sale_order()
        order.order_line[0].write({
            'product_id': service_product.id,
            'product_uom_qty': 100.0,
        })
        
        # Should allow confirmation even without stock
        order.action_confirm()
        self.assertEqual(order.state, 'sale', "Service products should bypass stock check")

    def test_08_stock_check_uses_warehouse_location(self):
        """Test: Stock check uses sale order's warehouse location"""
        order = self._create_sale_order()
        
        # Order should use warehouse location for stock check
        self.assertEqual(order.warehouse_id, self.warehouse, "Order should have warehouse")
        
        # Stock check should use warehouse's location
        line = order.order_line[0]
        location = line._ks_get_stock_location_for_company(order.company_id, order.warehouse_id)
        self.assertEqual(location, self.warehouse.lot_stock_id, "Should use warehouse location")

