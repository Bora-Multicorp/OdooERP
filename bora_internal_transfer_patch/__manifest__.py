# -*- coding: utf-8 -*-
{
    'name': 'Bora Internal Transfer Patch',
    'version': '18.0.1.0.0',
    'summary': 'Internal transfer issue fixes patch for inter-company lot sync, PO approval bypass, and quant validations',
    'description': """
        This module provides patch fixes for internal transfer issues:
        - Bypasses purchase order approval workflow for inter-company auto-generated purchase orders.
        - Bidirectional sync of move line lots, serials, IMEIs, and origins between inter-company delivery and receipt pickings.
        - Scopes IMEI and serial uniqueness checks to active company, positive quantities, and internal locations to prevent invalid blockages during transfers.
        - Allows easy uninstallation if patch is no longer required.
    """,
    'author': 'Bora Multicorp',
    'category': 'Inventory/Stock',
    'depends': [
        'base',
        'stock',
        'purchase',
        'sale_management',
        'ks_product_master',
        'ks_purchase_approval',
        'ks_sale_order',
    ],
    'data': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
