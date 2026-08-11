# -*- coding: utf-8 -*-

{
    'name': 'KS Exchange Rate',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Extended Exchange Rate Functionality with Exchanged Amount Calculation',
    'description': """
        KS Exchange Rate Module
        =======================
        
        This module extends the exchange_currency_rate module functionality by adding
        exchanged amount calculation for Sale Orders, Customer Invoices, and Purchase Orders.
        
        Features:
        - Exchange rate field (extends existing exchange_currency_rate module)
        - Exchanged amount field (calculated as: document_total / exchange_rate)
        - Automatic calculation when exchange rate or document total changes
        - Proper handling of different currencies between pricelist and document currency
        - Consistent logic across Sale Orders, Invoices, and Purchase Orders
    """,
    'author': 'Ksolves',
    'depends': ['base', 'sale_management', 'purchase', 'account', 'exchange_currency_rate'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/purchase_order_views.xml',
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

