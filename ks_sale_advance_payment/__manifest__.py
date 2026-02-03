# -*- coding: utf-8 -*-

{
    'name': "Sale Advance Payment",
    'summary': "Create advance payment directly from Sale Order without invoice",
    'version': '18.0.1.0.0',
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_advance_payment_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

