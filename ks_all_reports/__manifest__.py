# -*- coding: utf-8 -*-
{
    'name': 'KS All Reports',
    'version': '18.0.1.0.0',
    'summary': 'Part Wise All Data XLSX Report',
    'description': """
        KS All Reports Module
        ====================
        
        This module extends the Sales application with XLSX reporting functionality.
        
        Features:
        - Part Wise All Data XLSX Report
        - Direct download on menu click (no wizard required)
        - Predefined column headings for comprehensive reporting
        - Professional XLSX formatting with headers, colors, and frozen rows
    """,
    'category': 'Sales/Reporting',
    'author': 'Ksolves',
    'website': '',
    'depends': ['sale', 'stock', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

