# -*- coding: utf-8 -*-
{
    'name': 'Multi-Level Chart of Accounts Hierarchy',
    'version': '18.0.1.0.0',
    'summary': 'Layered parent-child Chart of Accounts with configurable depth levels',
    'description': """
Multi-Level Chart of Accounts Hierarchy (layered_coa)
======================================================
Extends Odoo 18 Accounting to support configurable multi-level parent-child
account relationships. Key features:

- Configure maximum CoA hierarchy depth per company
- Assign parent accounts to create tree structures
- Restrict journal postings to leaf (child) accounts only
- Auto-deprecate parent accounts when children are assigned
- Visual hierarchy columns in Chart of Accounts list view
- Grouped hierarchy display in all standard financial reports
- Full audit trail via Odoo Discuss (mail.thread)

Developed by: Ksolves India Limited
BRD Version:  V1.0 — 05-Jun-2026
    """,
    'author': 'Ksolves India Limited',
    'website': 'https://www.ksolves.com',
    'category': 'Accounting/Accounting',
    'license': 'LGPL-3',
    'depends': [
        'account',          # Invoicing / Accounting
        'account_accountant',  # Odoo 18 Enterprise Accounting
        'mail',             # Discuss — for chatter/audit trail
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/layered_coa_data.xml',
        'views/res_config_settings_views.xml',
        'views/account_account_views.xml',
    ],
    'assets': {
        'web.assets_backend': [],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
