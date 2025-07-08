# -*- coding: utf-8 -*-
{
    'name': "Bora Product Master",

    'summary': "Bora product master",

    'description': """

    """,

    'author': "Bora Multicorp",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'stock',  'product_multi_company', 'product_multi_images', 'product_dimension', 'product_approval'],
    'assets': {
        'web.assets_backend': [
            '/bora_product_master/static/src/js/stock_barcode_extension.js',
        ],
    },

    # always loaded
    'data': [
        'data/product_type.xml',
        'data/product_sku_sequance.xml',
        'views/stock_move_inherit_view.xml',
        'views/product_template_inherit_view.xml',
        'views/stock_quant_inherit_view.xml',
        'views/imei_search.xml',
        'views/product_product_inherit_view.xml',
        'views/sku_internal_ref_search.xml',
        'security/ir.model.access.csv',
        # 'views/barcode_loader.xml',
        # 'security/ir_rules.xml'
        # 'views/templates.xml',
        'views/assets.xml',
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
    'application': True,
    'installable': True,
    'license': 'Other proprietary',
}

