# -*- coding: utf-8 -*-
{
    'name': "Purchase Order Otek Report",
    'summary': "Excel report for Purchase Orders with Otek brand products",
    'category': 'Purchase',
    'version': '0.1',
    'license': 'LGPL-3',
    'depends': ['purchase', 'product', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_order_views.xml',
        'views/purchase_order_report_menu.xml',
    ],
}
