# -*- coding: utf-8 -*-
"""Common test setup for ks_templates module"""

from odoo.tests.common import TransactionCase
from datetime import date


class KsTemplatesCommon(TransactionCase):
    """Common setup for ks_templates tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
            'vat': '27AAVFB3612J1Z7',
        })
        
        # Create company partner with address
        country_india = cls.env.ref('base.in') if cls.env.ref('base.in', raise_if_not_found=False) else cls.env['res.country'].search([('code', '=', 'IN')], limit=1)
        state_mh = cls.env.ref('base.state_in_mh', raise_if_not_found=False) or False
        
        cls.company_partner = cls.env['res.partner'].create({
            'name': 'Test Company',
            'street': 'Gala No.15 S No.32/38,32/28/2',
            'street2': 'Pisoli Road, Kondwa, Taluka Haveli',
            'city': 'Pune',
            'zip': '411028',
            'country_id': country_india.id if country_india else False,
            'state_id': state_mh.id if state_mh else False,
            'is_company': True,
        })
        cls.company.partner_id = cls.company_partner
        
        # Create customer partner
        country_russia = cls.env.ref('base.ru') if cls.env.ref('base.ru', raise_if_not_found=False) else cls.env['res.country'].search([('code', '=', 'RU')], limit=1)
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'street': 'Office 5, building 3, 155',
            'street2': '100-Let Vladivostoku Ave.',
            'city': 'Vladivostok',
            'country_id': country_russia.id if country_russia else False,
            'customer_rank': 1,
        })
        
        # Create supplier partner
        cls.supplier = cls.env['res.partner'].create({
            'name': 'Test Supplier',
            'street': 'Supplier Street',
            'city': 'Mumbai',
            'country_id': country_india.id if country_india else False,
            'supplier_rank': 1,
        })
        
        # Create product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'sale_ok': True,
            'purchase_ok': True,
            'list_price': 100.0,
            'standard_price': 80.0,
            'weight': 1.5,
        })
        
        # Create product template with dimensions
        cls.product_template = cls.product.product_tmpl_id
        if hasattr(cls.product_template, 'product_length'):
            cls.product_template.write({
                'product_length': 50.0,
                'product_width': 30.0,
                'product_height': 25.0,
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
        
        # Create purchase order
        cls.purchase_order = cls.env['purchase.order'].with_company(cls.company).create({
            'partner_id': cls.supplier.id,
            'company_id': cls.company.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_qty': 5.0,
                'price_unit': 80.0,
            })],
        })
        
        # Create stock picking (delivery)
        cls.stock_picking = cls.env['stock.picking'].with_company(cls.company).create({
            'partner_id': cls.customer.id,
            'company_id': cls.company.id,
            'picking_type_id': cls.env.ref('stock.picking_type_out').id,
            'location_id': cls.env.ref('stock.stock_location_stock').id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
            'sale_id': cls.sale_order.id,
        })
        
        # Create stock move
        cls.stock_move = cls.env['stock.move'].create({
            'name': cls.product.name,
            'product_id': cls.product.id,
            'product_uom_qty': 10.0,
            'product_uom': cls.product.uom_id.id,
            'picking_id': cls.stock_picking.id,
            'location_id': cls.env.ref('stock.stock_location_stock').id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
        })
        
        # Create stock move line
        cls.stock_move_line = cls.env['stock.move.line'].create({
            'move_id': cls.stock_move.id,
            'product_id': cls.product.id,
            'product_uom_id': cls.product.uom_id.id,
            'qty_done': 10.0,
            'location_id': cls.env.ref('stock.stock_location_stock').id,
            'location_dest_id': cls.env.ref('stock.stock_location_customers').id,
        })
        
        # Create currency (AED)
        cls.currency_aed = cls.env['res.currency'].search([('name', '=', 'AED')], limit=1)
        if not cls.currency_aed:
            cls.currency_aed = cls.env['res.currency'].create({
                'name': 'AED',
                'symbol': 'AED',
                'decimal_places': 2,
            })
        
        # Create currency (INR)
        cls.currency_inr = cls.env['res.currency'].search([('name', '=', 'INR')], limit=1)
        if not cls.currency_inr:
            cls.currency_inr = cls.env['res.currency'].create({
                'name': 'INR',
                'symbol': '₹',
                'decimal_places': 2,
            })

