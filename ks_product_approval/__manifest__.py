# -*- coding: utf-8 -*-
{
    'name': "product Approval",
    'summary': "Product Approval",
    'category': 'Uncategorized',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base', 'product', 'stock', 'bus', 'product_dimension', 'ks_product_master', 'product_multi_company'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/approve_request_views.xml',
        'wizard/reject_request_views.xml',
        'wizard/bulk_submit_for_approval.xml',
        'wizard/approval_users_picker_wizard.xml',
        'wizard/suspended_by_admin_wizard.xml',
        'views/res_users_views.xml',
        'views/product_approval_res_config.xml',
        'views/product_approval_views.xml',
        'views/action_product_approval_view.xml',
        'views/search_view_for_activity.xml',
        # 'views/bulk_approval_and_rejection_menu.xml',
        'data/product_mail_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ks_product_approval/static/src/xml/ribbon.xml',
            'ks_product_approval/static/src/css/custom_style.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'Other proprietary',
}
