# -*- coding: utf-8 -*-
{
    'name': 'KS GRN Mismatch Approval',
    'version': '18.0.1.0.0',
    'summary': 'Restrict GRN validation on quantity/product mismatch and require PO approver approval',
    'description': """
        GRN Mismatch Approval
        ======================
        - Blocks receipt validation when received qty exceeds PO demand or when new products (not on PO) are added.
        - Sends approval request to the PO's approvers (Approver 1 / Approver 2 from ks_purchase_approval), not the buyer.
        - After approval, PO is updated manually; warehouse responsible person is notified.
    """,
    'category': 'Inventory/Inventory',
    'author': 'Ksolves',
    'website': '',
    'depends': ['purchase_stock', 'ks_purchase_approval', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/ks_grn_mismatch_approval_views.xml',
        'views/stock_picking_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/ks_grn_mismatch_approve_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
