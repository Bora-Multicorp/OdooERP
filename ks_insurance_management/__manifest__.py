# -*- coding: utf-8 -*-
{
    'name': 'KS Insurance Management',
    'version': '18.0.1.1.0',
    'category': 'Accounting',
    'summary': 'Comprehensive Insurance Policy Management with Declarations and Reports',
    'icon': '/ks_insurance_management/static/description/icon.png',
    'description': """
        KS Insurance Management
        =========================
        - Insurance policies (individual & floater) with types and categories
        - Insurance companies and agents
        - Marine, Fire & Burglary, and Miscellaneous reports
        - Declarations (marine sales / fire & burglary inventory) with email and PDF
        - Payment-linked policy creation and expiry reminders
        - Multi-company and multi-currency support
        - Record rules and access rights for User and Administrator roles
    """,
    'author': 'Ksolves',
    'website': 'https://www.ksolves.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'mail',
        'stock',
    ],
    'data': [
        'security/insurance_security.xml',
        'security/ks_insurance_record_rules.xml',
        'security/ir.model.access.csv',
        'data/insurance_sequence.xml',
        'data/insurance_category_data.xml',
        'data/insurance_type_data.xml',
        'data/insurance_cron.xml',
        'data/insurance_mail_templates.xml',
        'views/insurance_type_views.xml',
        'views/insurance_policy_views.xml',
        'views/insurance_declaration_views.xml',
        'views/insurance_menu.xml',
        'report/report_templates.xml',
        # 'data/test_demo_data.xml',      # TESTING ONLY — remove this line and delete the file when done
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
