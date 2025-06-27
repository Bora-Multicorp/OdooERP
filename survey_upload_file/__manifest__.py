# -*- coding: utf-8 -*-

{
    'name': "File Upload In Survey",
    'version': "18.0.1.0.0",
    'category': 'Extra Tools',
    'summary': 'Attachment of File in Survey Form',
    'description': 'This module is used for attachments of file in Survey Form,'
                   'You can also add multiple file attachment to Survey Form .',
    'website': '',
    'depends': ['survey', 'whatsapp'],
    'assets': {
        'survey.survey_assets': [
            'survey_upload_file/static/src/js/survey_form_attachment.js',
            'survey_upload_file/static/src/js/SurveyFormWidget.js',
        ],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/vendor_kyc_data.xml',
        'wizard/survey_invite_inherit.xml',
        'views/survey_question_views.xml',
        'views/survey_user_views.xml',
        'views/survey_views.xml',
        'views/survey_templates.xml',
        'views/res_partner_views.xml',
    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
