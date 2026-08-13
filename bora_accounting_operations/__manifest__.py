# -*- coding: utf-8 -*-
{
    'name': 'Bora Accounting Operations',
    'version': '18.0.1.0.0',
    'summary': 'Custom accounting operations including bank statement line debit and credit display',
    'category': 'Accounting/Accounting',
    'author': 'Bora Multicorp',
    'depends': ['account', 'account_accountant'],
    'data': [
        'views/account_bank_statement_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
