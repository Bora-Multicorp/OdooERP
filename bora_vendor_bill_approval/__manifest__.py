# -*- coding: utf-8 -*-
{
    'name': 'Bora Vendor Bill Approval',
    'version': '18.0.1.0.0',
    'summary': 'Multi-level approval workflow for Vendor Bills (Confirm / action_post)',
    'category': 'Accounting/Accounting',
    'author': 'Bora Multicorp',
    'depends': ['account', 'purchase', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/bora_vendor_bill_approval_data.xml',
        'wizard/bora_vendor_bill_approval_request_wizard_views.xml',
        'wizard/bora_vendor_bill_approval_reason_wizard_views.xml',
        'views/bora_vendor_bill_approval_config_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
