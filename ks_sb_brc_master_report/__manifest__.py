# -*- coding: utf-8 -*-
{
    'name': 'SB/BRC Master Report',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Master report for Shipping Bill (SB) and Bank Realization Certificate (BRC) data',
    'author': 'BORA',
    'depends': [
        'base',
        'account',
        'sale',
        'stock',
        'product',
        'l10n_in',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sb_brc_master_views.xml',
        'views/menu_actions.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
