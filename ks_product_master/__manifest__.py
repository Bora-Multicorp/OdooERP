# -*- coding: utf-8 -*-
{
    'name': "Bora Product Master",
    'summary': "Bora product master",
    'description': """
    """,
    'author': "Ksolves Private Limited",
    'website': "https://www.ksolves.com/",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'stock', 'stock_account', 'sale_project', 'purchase', 'account', 'mail', 'l10n_in_withholding'],

    # always loaded
    'data': [
        'security/ir_rules.xml',
        'security/ir.model.access.csv',
        'data/product_categories.xml',
        'data/product_sku_sequance.xml',
        'data/brand_realme.xml',
        'data/inventory_traceability_config.xml',
        'views/account_move_view.xml',
        'views/stock_move_inherit_view.xml',
        'views/stock_valuation_layer_views.xml',
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
        'wizards/activation_status_wizard_view.xml',
        'wizards/stock_move_upload_csv_wizard_view.xml',
        'views/stock_traceability_report_pdf.xml',
        'views/margin_analysis_report_views.xml',
        'views/ad_margin_report_views.xml',
        'views/mop_master_views.xml',
        'views/tds_wizard_view_inherit.xml',
        'views/purchase_order_inherit_view.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'ks_product_master/static/sample/IMEI_ACTIVATION_SAMPLE_REPORT.xlsx',
            'ks_product_master/static/src/js/barcode_focus_change.js',
            'ks_product_master/static/src/xml/stock_traceability_report.xml',
        ],
    },


    'application': True,
    'installable': True,
    'license': 'Other proprietary',

    # Required for Excel (.xlsx) import in Upload Serials/Lots wizard
    'external_dependencies': {
        'python': ['openpyxl'],
    },
}

