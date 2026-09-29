# -*- coding: utf-8 -*-
{
    'name': 'Bora Chart of Accounts (COA)',
    'version': '18.0.1.0.0',
    'summary': 'Chart of accounts updates (900001-900004) and country-based contact accounts',
    'description': """Chart of Accounts customization for Bora:
Updates 600292 to 900001 Domestic Debtor and 600291 to 900002 Domestic Creditor.
Creates 900003 Export Debtor and 900004 Export Creditor.
Updates contact form receivable and payable accounts based on country match.""",
    'category': 'Accounting/Accounting',
    'author': 'Bora Multicorp',
    'depends': ['base', 'account', 'contacts'],
    'data': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
