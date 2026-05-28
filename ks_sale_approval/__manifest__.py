# -*- coding: utf-8 -*-
{
    'name': 'KS Sale Order Approval Workflow',
    'version': '18.0.1.1.0',
    'summary': 'Multi-level approval workflow for Sale Orders with PM approvers',
    'description': """
        Custom Approval Workflow for Sale Orders
        =========================================
        
        This module provides a comprehensive approval workflow for Sale Orders:
        
        PM Users:
        - Full access to Sale Orders
        - Can edit prices
        - Can confirm Sale Orders directly without approval
        
        Normal Users:
        - Can create Sale Orders
        - Cannot change item prices
        - Cannot confirm Sale Orders directly
        - Clicking Confirm sends SO to "Approval Pending" state
        - Clicking Cancel sends SO to "Cancel Pending" state
        
        Approval Logic:
        - Single PM: One approval confirms the SO
        - Two PMs: Both must approve before SO is confirmed
        
        Features:
        - Configure up to two PM approvers
        - Normal users can only request actions (confirm, cancel)
        - PM users can approve or reject requests with reasons
        - Complete audit trail in chatter
        - SO locked during approval states
        - Clear status labels for pending states
    """,
    'category': 'Sales/Sales',
    'author': 'Ksolves',
    'website': '',
    'depends': ['sale', 'sales_team', 'mail', 'purchase', 'stock', 'ks_product_master', 'ks_product_approval'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ks_approval_data.xml',
        'data/mail_templates.xml',
        'wizard/ks_reject_reason_wizard_views.xml',
        'wizard/ks_approval_request_wizard_views.xml',
        'wizard/ks_cancel_approval_request_wizard_views.xml',
        'wizard/ks_edit_approval_request_wizard_views.xml',
        'wizard/ks_approval_reason_wizard_views.xml',
        'wizard/ks_delivery_approval_request_wizard_views.xml',
        'wizard/ks_delivery_approval_reason_wizard_views.xml',
        'wizard/ks_pod_upload_wizard_views.xml',
        'views/ks_sale_approval_config_views.xml',
        'views/sale_order_views.xml',
        'views/product_views.xml',
        'views/ks_delivery_approval_config_views.xml',
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

