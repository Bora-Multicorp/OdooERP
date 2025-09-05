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
    'depends': ['base', 'product', 'stock', 'purchase','sale_project', 'sale_management', 'product_multi_company', 'product_multi_images', 'product_dimension', 'case_sensitive_widget', 'stock_barcode'],

    # always loaded
    'data': [
        'data/product_categories.xml',
        'data/product_sku_sequance.xml',
        'data/inventory_traceability_config.xml',
        'views/stock_move_inherit_view.xml',
        'views/product_template_inherit_view.xml',
        'views/stock_quant_inherit_view.xml',
        'views/imei_search.xml',
        'views/product_product_inherit_view.xml',
        'views/sku_internal_ref_search.xml',
        'views/product_creation_from_po_block.xml',
        'views/product_category_inherit.xml',
        'views/show_hide_product_fields.xml',
        'views/product_context_change.xml',
        'views/product_template_tree_view.xml',
        'views/IFSC_and_branch_code.xml',
        'wizards/activation_status_wizard_view.xml',
        'security/ir.model.access.csv',
        # 'static/src/xml/assets.xml',
        # 'views/barcode_loader.xml',
        # 'security/ir_rules.xml'
        # 'views/templates.xml',
    ],

    'assets': {
        'web.assets_backend': [
            '/bora_product_master/static/sample/IMEI_ACTIVATION_SAMPLE_REPORT.xlsx',
            '/bora_product_master/static/src/js/barcode_focus_change.js',
        ],
    },

    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
    'application': True,
    'installable': True,
    'license': 'Other proprietary',
}

