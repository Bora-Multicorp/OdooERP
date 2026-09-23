# -*- coding: utf-8 -*-
{
    'name': 'Bora Account TDS',
    'version': '18.0.1.0.0',
    'summary': 'Fix Indian TDS tax visibility and configuration for sub-companies and branches',
    'description': """
Bora Account TDS
================
Allows sub-companies (branches) to access and apply Indian TDS withholding taxes configured on the parent company.
    """,
    'category': 'Accounting/Localizations',
    'author': 'Bora Multicorp',
    'website': 'https://boramobility.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'l10n_in_withholding',
        'ks_product_master',
    ],
    'data': [
        'views/l10n_in_withhold_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
