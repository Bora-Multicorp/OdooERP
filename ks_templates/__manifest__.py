# -*- coding: utf-8 -*-

{
    'name': "Warehouse Extension",
    'version': "18.0.1.0.0",
    'category': 'Extra Tools',
    'summary': 'Extended features of warehouse',
    'description': 'This module is used for attachments of file in Survey Form,'
                   'You can also add multiple file attachment to Survey Form .',
    'author': 'Ksolves Private Limited',
    'website': 'https://www.ksolves.com/',
    'depends': ['quality','sale','stock','account'],
    'assets': {

    },
    'data': [
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'report/dubai_sales_report_template.xml',
        'report/luminari_report.xml',
        'report/purchase_report.xml',
        'report/savex_purchase_report.xml',
        'report/invoice_report_with_gst.xml',
        'report/invoice_report_without_gst.xml',
        'report/packing_list_report.xml',
        # 'report/SRLLP_puchase_report.xml',


    ],
    'images': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
