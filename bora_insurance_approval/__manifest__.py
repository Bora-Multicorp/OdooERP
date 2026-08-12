# -*- coding: utf-8 -*-
{
    'name': 'Bora Insurance Approval',
    'version': '18.0.1.0.0',
    'summary': 'Multi-level approval workflow for Insurance Policies Payment Request',
    'category': 'Services/Insurance',
    'author': 'Bora Multicorp',
    'depends': ['ks_insurance_management', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/bora_insurance_approval_data.xml',
        'wizard/bora_insurance_approval_request_wizard_views.xml',
        'wizard/bora_insurance_approval_reason_wizard_views.xml',
        'views/bora_insurance_approval_config_views.xml',
        'views/insurance_policy_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
