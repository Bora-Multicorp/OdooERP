# -*- coding: utf-8 -*-
{
    'name': 'Bora PO Terms & Conditions',
    'version': '18.0.1.0.0',
    'summary': 'Default Terms and Conditions for Purchase Orders in Settings and Purchase Orders',
    'category': 'Purchases',
    'author': 'Bora Multicorp',
    'depends': [
        'purchase',
    ],
    'data': [
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/purchase_terms_template.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
