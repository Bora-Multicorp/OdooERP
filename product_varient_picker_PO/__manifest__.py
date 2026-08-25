# -*- coding: utf-8 -*-
{
    'name': 'Product Variant Picker for Purchase Order',
    'version': '1.0',
    'category': 'Inventory/Purchase',
    'summary': 'Product variant picker dialog for purchase order line items',
    'description': """
Product Variant Picker for Purchase Order
==========================================

This module brings the product variant picker dialog to Purchase Order line items,
matching the behavior in Sales Orders.

Features:
- Allows selecting Product Template in Purchase Order line items.
- Opens Variant Picker Modal (ProductConfiguratorDialog) when selecting a product with variants.
- Automatically sets product variant and attribute values on Purchase Order lines.
- Adds edit configuration option for configurable products on PO lines.
    """,
    'author': 'SunArc Technologies Private Limited',
    'website': 'https://sunarctechnologies.com/',
    'depends': ['purchase', 'sale'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_varient_picker_PO/static/src/js/purchase_product_field.js',
            'product_varient_picker_PO/static/src/js/purchase_product_field.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
