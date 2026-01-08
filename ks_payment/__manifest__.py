# -*- coding: utf-8 -*-
{
    'name': 'KS Payment Access Control',
    'version': '18.0.1.0.0',
    'summary': 'Group-based access control for account.payment using single security group',
    'description': """
        KS Payment Access Control
        =========================
        
        This module implements group-based access control for account.payment ONLY:
        
        Features:
        - Single security group: "KS Payment Access"
        - Only users in this group can view, create, and edit account.payment records
        - All other users are completely blocked from accessing payments
        - Sales Team users CANNOT access payments but CAN continue accessing Sale Orders normally
        - Clean implementation using model access rights and minimal record rules
        
        Important:
        - This module restricts ONLY account.payment model
        - Sale Orders (sale.order) are NOT affected
        - Sales module functionality remains completely unaffected
        - Sales Team users retain full access to Sale Orders
        
        Security Implementation:
        - Security group defined in security/groups.xml
        - Model access rights in security/ir.model.access.csv (account.payment only)
        - Minimal record rules scoped to account.payment model only
        - Follows Odoo best practices
        - No global restrictions, isolated to payments only
    """,
    'category': 'Accounting/Accounting',
    'author': 'Ksolves',
    'website': '',
    'depends': ['account'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/payment_security.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

