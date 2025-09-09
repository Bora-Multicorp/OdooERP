# -*- coding: utf-8 -*-
{
    'name': "bora_purchase",

    'summary': "Bora purchase operations",

    'description': """
Bora purchase operations
    """,

    'author': "Bora",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Purchase',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase','purchase_stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/po_lock_unlock/po_unlock_approve_request_wizard.xml',
        'wizard/po_lock_unlock/po_unlock_reject_request_wizard.xml',
        'wizard/po_confirm_approval/po_confirm_approve_request_wizard.xml',
        'wizard/po_confirm_approval/po_confirm_reject_request_wizard.xml',
        'wizard/po_confirm_approval/confirmation_approval_users_picker_wizard.xml',
        'wizard/po_confirm_approval/confirmation_suspended_by_admin_wizard.xml',
        'wizard/po_cancel_approval/po_cancel_approve_request_wizard.xml',
        'wizard/po_cancel_approval/po_cancel_reject_request_wizard.xml',
        'wizard/po_cancel_approval/cancelation_approval_users_picker_wizard.xml',
        'wizard/po_cancel_approval/cancelation_suspended_by_admin_wizard.xml',
        # 'views/qc_check_on_delivery.xml',
        'views/vendor_payment_email_template.xml',
        'views/unlock_approvers.xml',
        'views/confirmation_approvers.xml',
        'views/cancallation_approvers.xml',
        'views/po_unlock.xml',
        'views/po_fullfill_by.xml',
        'views/po_confirm.xml',
        'views/po_cancellation.xml'
    ],
    'assets': {
        'web.assets_backend': [
            '/bora_purchase/static/src/js/switch_tab.js',
        ],
    },

    'application': True,
    'installable': True,
    'license': 'Other proprietary'
}

