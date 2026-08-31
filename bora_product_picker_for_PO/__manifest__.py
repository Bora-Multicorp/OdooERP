{
    'name': 'Bora Product Picker for PO',
    'version': '18.0.1.0',
    'category': 'Purchases',
    'summary': 'Variant/configuration picker for purchase order product lines',
    'description': """
Bora Product Picker for PO
=========================

This module brings the sales-order product configurator flow to purchase order lines,
so configurable and variant products can be selected from the same product picker
wizard when creating purchase order lines.
    """,
    'author': 'Bora',
    'depends': ['purchase', 'sale'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'bora_product_picker_for_PO/static/src/js/purchase_product_field.js',
            'bora_product_picker_for_PO/static/src/js/purchase_product_field.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
