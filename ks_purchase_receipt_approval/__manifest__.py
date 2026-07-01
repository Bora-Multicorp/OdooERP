# -*- coding: utf-8 -*-
{
    'name': 'KS Purchase Receipt Approval',
    'version': '18.0.1.0.0',
    'summary': 'Multi-level approval workflow for Purchase Receipts (Incoming Shipments)',
    'category': 'Inventory/Purchase',
    'author': 'Ksolves',
    'depends': ['purchase', 'stock', 'mail', 'ks_product_approval'],
    'data': [
        'security/ir.model.access.csv',
        'data/ks_purchase_receipt_approval_data.xml',
        'wizard/ks_purchase_receipt_approval_request_wizard_views.xml',
        'wizard/ks_purchase_receipt_approval_reason_wizard_views.xml',
        'views/ks_purchase_receipt_approval_config_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
