# -*- coding: utf-8 -*-
{
    'name': 'Bora Inventory Operations',
    'version': '18.0.1.0.0',
    'summary': 'Inventory operations custom enhancements including Latest Purchase Price, Latest Sales Price, Pick-up Details, and Transporter Vendor Bill Generation',
    'category': 'Inventory/Inventory',
    'author': 'Bora Multicorp',
    'depends': [
        'stock',
        'purchase',
        'sale',
        'account',
        'stock_delivery',
        'odx_m2m_attachment_preview',
    ],
    'data': [
        'views/product_product_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
