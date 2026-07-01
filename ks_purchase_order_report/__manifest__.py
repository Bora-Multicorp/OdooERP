# -*- coding: utf-8 -*-
{
    'name': "Purchase Order Otek Report",
    'summary': "Tree view and Excel report for Purchase Orders with Otek brand products",
    'category': 'Purchase',
    'version': '0.2',
    'license': 'LGPL-3',
    'depends': ['purchase', 'product', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_order_otek_report_wizard_views.xml',
        # 'views/purchase_order_views.xml',
        'views/purchase_order_report_menu.xml',
    ],
}
