# -*- coding: utf-8 -*-

{
    'name': "Purchase Advance Payment",
    'summary': "Advance payment from PO, vendor payment approval (with/without bill), approval settings",
    'version': '18.0.2.0.0',
    'depends': ['purchase', 'account', 'mail', 'ks_payment_access_control','ks_sale_order'],
    'data': [
        'security/ir.model.access.csv',
        'data/advance_deduction_product.xml',
        'data/mail_template_banking_team.xml',
        'views/vendor_payment_approval_config_views.xml',
        'views/vendor_payment_approval_request_views.xml',
        'views/vendor_payment_approval_bulk_actions.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'views/purchase_order_menus.xml',
        'views/res_config_settings_views.xml',
        'wizard/purchase_advance_payment_views.xml',
        'wizard/vendor_payment_approval_approve_wizard_views.xml',
        'wizard/vendor_payment_approval_reject_wizard_views.xml',
        'wizard/vendor_payment_approval_submit_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
