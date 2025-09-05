{
    'name': 'Bora Sale/Purchase Order Approval',
    'version': '1.0',
    'summary': 'Adds a multi-level approval workflow to sales orders and purchase order.',
    'description': """
        This module provides a robust approval system for sales orders and purchase order, allowing you to define a sequence of approvers and track the approval status.
    """,
    'depends': ['sale', 'base','bus','account'],
    'data': [
        'data/payment_term.xml',
        'security/ir.model.access.csv',
        # 'wizard/approval_request.xml',
        # 'wizard/reject_request.xml',
        'wizard/payment_term_approval_request.xml',
        'wizard/payment_term_reject.xml',
        # 'wizard/cancel_approval_request.xml',
        #  'wizard/cancel_reject_request.xml',
        # 'views/sale_approval_res_config.xml',
        'views/payment_term_res_config.xml',
        # 'views/sale_confirmation_approval_views.xml',
        # 'views/sale_approval_views.xml',
        'views/payment_term_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}