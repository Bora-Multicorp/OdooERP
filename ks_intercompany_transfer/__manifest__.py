# -*- coding: utf-8 -*-
{
    'name': 'KS Inter-Company Transfer',
    'version': '18.0.1.0.0',
    'summary': 'Track total quantity of products transferred between companies',
    'description': """
        Inter-Company Transfer Tracking
        =================================
        Shows the total quantity of products transferred from one company's
        warehouse to another company's warehouse (done stock moves only).
        Adds a computed field on product (Inter-Company Transfer Qty) visible
        in the Stock report list view.
    """,
    'category': 'Inventory/Inventory',
    'author': 'Ksolves',
    'website': '',
    'depends': ['stock'],
    'data': [
        'views/product_product_views.xml',
        'views/stock_location.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
