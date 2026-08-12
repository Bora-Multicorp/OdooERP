# -*- coding: utf-8 -*-
{
    'name': 'Bora Journal Entries Approval',
    'version': '18.0.1.0.0',
    'summary': 'Multi-level approval workflow for Journal Entries (Post / action_post)',
    'category': 'Accounting/Accounting',
    'author': 'Bora Multicorp',
    'depends': ['account', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/bora_journal_entry_approval_data.xml',
        'wizard/bora_journal_entry_approval_request_wizard_views.xml',
        'wizard/bora_journal_entry_approval_reason_wizard_views.xml',
        'views/bora_journal_entry_approval_config_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
