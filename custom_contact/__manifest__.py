# -*- coding: utf-8 -*-
{
    'name': "Vendor KYC",

    'summary': "Custom Contact",
    'category': 'Uncategorized',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'account', 'accountant', 'purchase', 'sale'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/master_data.xml',
        'wizard/vendor_kyc_views.xml',
        'wizard/approve_request_views.xml',
        'wizard/reject_request_views.xml',
        'views/vendor_approval_res_config.xml',
        'views/custom_partner.xml',
        'views/master_view.xml',
        'views/vendor_approval_views.xml',
    ],

}
