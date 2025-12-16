# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Purchase Two Level Approval',
    'version': '18.0.1.0.0',
    'summary': 'Two-level Purchase Order approval workflow with PM roles',
    'description': """
        This module implements a 2-level Purchase Order approval workflow with:
        - Custom user roles (Normal User, PM, A/C Head)
        - PO locking rules for normal users
        - PM-level permissions for approval and direct confirmation
        - Two PM approval tracking (pm1_approved, pm2_approved)
        - Special "Confirm as PM" button for PM/A/C Head users
        - PM Approval tab on PO form
    """,
    'category': 'Inventory/Purchase',
    'author': 'Shakawear',
    'website': 'https://www.shakawear.com',
    'license': 'LGPL-3',
    'depends': [
        'purchase',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/po_approval_user_view.xml',
        'views/purchase_order_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

