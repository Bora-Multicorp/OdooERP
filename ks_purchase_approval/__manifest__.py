# -*- coding: utf-8 -*-
{
    'name': 'KS Purchase Order Multi-Level Approval',
    'version': '18.0.1.0.0',
    'summary': 'Multi-level approval workflow for Purchase Orders with PM1 & PM2 approvers',
    'description': """
        Custom Multi-Level Approval Workflow for Purchase Orders
        =========================================================
        
        This module provides a comprehensive approval workflow for:
        - PO Confirmation Approval (both PM1 and PM2 must approve)
        - PO Update Request and Approval
        - PO Cancel Request and Approval
        
        Features:
        - Configure two approval managers (PM1 & PM2)
        - Normal users can only request actions (confirm, update, cancel)
        - PM users can approve or reject requests with reasons
        - Complete audit trail in chatter
        - PO locked during approval states
    """,
    'category': 'Inventory/Purchase',
    'author': 'Ksolves',
    'website': '',
    'depends': ['purchase', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ks_approval_data.xml',
        'wizard/ks_request_reason_wizard_views.xml',
        'wizard/ks_reject_reason_wizard_views.xml',
        'wizard/ks_approval_confirmation_wizard_views.xml',
        'wizard/ks_approve_confirmation_reason_wizard_views.xml',
        'wizard/ks_approve_update_reason_wizard_views.xml',
        'views/ks_purchase_approval_config_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
