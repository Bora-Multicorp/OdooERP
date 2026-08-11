# -*- coding: utf-8 -*-
{
    'name': 'Bora Credit Note Approval',
    'version': '18.0.1.0.0',
    'summary': 'Multi-level approval workflow for Vendor and Customer Credit Notes (Confirm / action_post)',
    'category': 'Accounting/Accounting',
    'author': 'Bora Multicorp',
    'depends': ['account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/bora_credit_note_approval_data.xml',
        'wizard/bora_credit_note_approval_request_wizard_views.xml',
        'wizard/bora_credit_note_approval_reason_wizard_views.xml',
        'views/bora_credit_note_approval_config_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
