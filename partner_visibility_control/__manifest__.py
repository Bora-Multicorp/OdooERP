# -*- coding: utf-8 -*-
{
    'name': 'Partner Visibility Control',
    'version': '18.0.1.0.1',
    'category': 'Custom',
    'summary': (
        'Restrict partner_id dropdown in Sales and Purchase orders '
        'to contacts assigned to the current user.'
    ),
    'description': """
        Adds salesperson_ids and purchase_executive_ids (Many2many → res.users)
        to res.partner.

        - Sales Orders : partner_id dropdown only shows partners where the
          current user is in salesperson_ids.
        - Purchase Orders : partner_id dropdown only shows partners where the
          current user is in purchase_executive_ids.
        - Admin / superuser always sees all contacts.
        - Auto-assigns the current user to the partner on order creation when
          they are not already assigned.

        Visibility is enforced via:
        - A global ir.rule: contacts are visible only when the current user is
          in salesperson_ids, or when no sales executives are assigned yet.
        - View-level domain filters for Sales/Purchase order dropdowns.
    """,
    'author': 'Custom Development',
    'depends': ['sale_management', 'purchase', 'ks_contact', 'contacts'],
    'data': [
        'security/security_groups.xml',
        'security/ir_rule.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
