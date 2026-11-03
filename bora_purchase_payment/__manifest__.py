# -*- coding: utf-8 -*-
{
    'name': 'Bora Purchase Payment',
    'version': '18.0.1.0.0',
    'summary': 'Automatic vendor payment creation on approval, payment linking, memo formatting and terminology customization',
    'category': 'Purchase',
    'author': 'Bora Multicorp',
    'depends': [
        'purchase',
        'account',
        'ks_purchase_advance_payment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_activity_data.xml',
        'views/banking_approval_config_views.xml',
        'views/vendor_payment_approval_request_views.xml',
        'views/account_payment_views.xml',
        'views/purchase_order_views.xml',
        'wizard/purchase_advance_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
