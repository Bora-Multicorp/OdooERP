# -*- coding: utf-8 -*-
{
    'name': "Vendor KYC",

    'summary': "Custom Contact",
    'category': 'Uncategorized',
    'version': '0.1',
    'license': 'LGPL-3',
    # any module necessary for this one to work correctly
    'depends': ['l10n_in','base', 'contacts', 'account', 'accountant', 'purchase', 'sale', 'survey', 'case_sensitive_widget', 'sh_survey_matrix_adv','base_multi_company', 'ks_contact_access_rights'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/master_data.xml',
        'data/mail_template_data.xml',
        'data/kyc_expiry_request_cron.xml',
        'data/vendor_kyc_data.xml',
        'wizard/vendor_kyc_views.xml',
        'wizard/approve_request_views.xml',
        'wizard/reject_request_views.xml',
        'wizard/re_kyc_request_views.xml',
        'wizard/survey_invite_inherit.xml',
        'wizard/vendor_kyc_approval_users_picker_wizard.xml',
        'wizard/vendor_suspended_by_admin_wizard.xml',
        'views/vendor_approval_res_config.xml',
        'views/custom_partner.xml',
        'views/master_view.xml',
        'views/survey_views.xml',
        'views/vendor_approval_views.xml',
        'views/survey_templates.xml',
        'views/contacts_field_changes.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ks_contact/static/src/css/kyc_form.css',
        ],
    },

}
