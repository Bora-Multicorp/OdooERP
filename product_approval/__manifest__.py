# -*- coding: utf-8 -*-
{
    'name': "product Approval",
    'summary': "Product Approval",
    'category': 'Uncategorized',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base', 'product'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/approve_request_views.xml',
        'wizard/reject_request_views.xml',
        'views/product_approval_res_config.xml',
        'views/product_approval_views.xml',
        'views/action_product_approval_view.xml',
        'data/product_mail_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_approval/static/src/xml/ribbon.xml',
        ],
    },
}
