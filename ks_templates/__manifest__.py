# -*- coding: utf-8 -*-

{
    'name': "Warehouse Extension",
    'version': "18.0.1.0.1",
    'category': 'Extra Tools',
    'summary': 'Extended features of warehouse',
    'description': 'This module is used for attachments of file in Survey Form,'
                   'You can also add multiple file attachment to Survey Form .',
    'author': 'Ksolves Private Limited',
    'website': 'https://www.ksolves.com/',
    'depends': ['quality', 'sale', 'stock', 'account', 'purchase', 'ks_sale_order', 'sale_stock', 'purchase_stock'],
    'assets': {
        'web.assets_backend': [
            'ks_templates/static/src/js/hide_packing_list_print.js',
        ],
    },
    'data': [
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/stock_picking_views.xml',
        'report/dubai_sales_report_template.xml',
        'report/domestic_sales_report.xml',
        'report/dubai_sales_report_template_inherit.xml',
        'report/dubai_sales_report_merge_to_base.xml',
        'report/luminari_report.xml',
        'report/purchase_report.xml',
        'report/purchase_report_merge_to_base.xml',
        'report/savex_purchase_report.xml',
        'report/invoice_report_with_gst.xml',
        'report/invoice_report_with_gst_inr.xml',
        'report/invoice_report_without_gst.xml',
        'report/invoice_report_without_gst_inr.xml',
        'report/invoice_report_domestic_tax.xml',
        'report/invoice_report_domestic_tax_usd.xml',
        'report/invoice_report_domestic_tax_inr_converted.xml',
        'report/invoice_luminari_merge_to_base.xml',
        'report/packing_list_report.xml',
        # 'report/SRLLP_puchase_report.xml',


    ],
    'images': [],
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
}
