# -*- coding: utf-8 -*-

{
    'name': 'KS Reports',
    'version': '18.0.1.0.0',
    'summary': 'Part Wise All Data XLSX Report',
    'description': """
        KS Reports Module
        =================
        
        This module extends the Sales application with XLSX reporting functionality.
        
        Features:
        - Part Wise All Data XLSX Report
        - Direct download on menu click (no wizard required)
        - Product-wise data display (each product on separate row)
        - Professional XLSX formatting with headers, colors, and frozen rows
    """,
    'category': 'Sales/Reporting',
    'author': 'Ksolves',
    'website': '',
    'depends': ['sale', 'sale_stock', 'account', 'web', 'ks_sale_advance_payment', 'purchase', 'ks_sale_order', 'ks_sb_brc_master_report'],
    'data': [
        'security/ir.model.access.csv',
        'data/sb_tracker_sequence.xml',
        'data/ks_purchase_report_cron.xml',
        'views/ks_report_line_views.xml',
        'views/sb_tracker_views.xml',
        'views/menu_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/ks_purchase_report_detail_views.xml',
        'views/stock_report_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'ks_reports/static/src/cog_menu_cn_tracking/cog_menu_cn_tracking.js',
            'ks_reports/static/src/cog_menu_cn_tracking/cog_menu_cn_tracking.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

