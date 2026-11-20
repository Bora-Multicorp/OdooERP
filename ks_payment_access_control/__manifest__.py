# -*- coding: utf-8 -*-
{
    'name': 'KS Payment Access Control',
    'version': '18.0.1.0.1',
    'summary': 'Restrict Payments menu and access to specific security group',
    'description': """
        KS Payment Access Control
        =========================
        
        This module restricts access to Payments (account.payment) menu and records:
        
        Features:
        - Creates a security group: "KS Payment Access"
        - Only users in this group can see the Payments menu
        - Only users in this group have read/write access to payments
        - Users not in the group cannot see the menu
        - Users not in the group cannot access payments via direct URL
        - Complete access control using security groups, access rights, and record rules
        
        Security Implementation:
        - Security group defined in security/groups.xml
        - Model access rights in security/ir.model.access.csv
        - Record rules to restrict access
        - Menu items hidden for users not in group
        - Access methods overridden to prevent direct URL access
    """,
    'category': 'Accounting/Accounting',
    'author': 'Ksolves',
    'website': '',
    'depends': ['account'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/payment_security.xml',
        'views/account_payment_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

