# -*- coding: utf-8 -*-

{
    'name': "Purchase Advance Payment",
    'summary': "Advance payment from PO, vendor payment approval (with/without bill), approval settings",
    'version': '18.0.1.0.0',
    'depends': ['purchase', 'account', 'mail', 'ks_payment_access_control'],
    'data': [
        'security/ir.model.access.csv',
        'data/advance_deduction_product.xml',
        'views/vendor_payment_approval_config_views.xml',
        'views/vendor_payment_approval_request_views.xml',
        'views/vendor_payment_approval_bulk_actions.xml',
        'views/purchase_order_views.xml',
        'views/purchase_order_menus.xml',
        'wizard/purchase_advance_payment_views.xml',
        'wizard/vendor_payment_approval_approve_wizard_views.xml',
        'wizard/vendor_payment_approval_reject_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
