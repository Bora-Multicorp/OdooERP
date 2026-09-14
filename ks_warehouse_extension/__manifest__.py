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
    'depends': ['quality', 'sale', 'ks_automail'],
    'assets': {

    },
    'data': [
        'report/qc_email_template.xml',
        'report/sale_order_mail_3pl.xml',
        'views/sale_order_view.xml',

    ],
    'images': [],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
