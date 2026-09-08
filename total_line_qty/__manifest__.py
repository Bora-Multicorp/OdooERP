# -*- coding: utf-8 -*-
{
    'name': 'Total Line Quantity on SO, PO, Invoice and Picking',
    'version': '18.0.1.0.0',
    'category': 'Sales/Purchases/Accounting/Inventory',
    'summary': 'Displays total quantity of line items in the list view aligned with the quantity column with label text.',
    'description': """
        This module adds a read-only line item total row at the bottom of the line items list table
        aligned with the Quantity column on Sale Orders, Purchase Orders, Invoices, and Stock Pickings.
    """,
    'author': 'Custom',
    'website': '',
    'depends': ['sale', 'purchase', 'account', 'stock'],
    'data': [
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'total_line_qty/static/src/js/list_renderer.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
