# -*- coding: utf-8 -*-
{
    'name': 'KS Auto Mail for Sale Orders',
    'version': '18.0.1.0.0',
    'summary': 'Automatic email notifications at Sale Order stages',
    'description': """
        KS Auto Mail Module
        ===================
        
        Automatically sends emails to customers at key Sale Order stages:
        
        Features:
        - Email when Sale Order is confirmed
        - Email when order is packed
        - Email when order is shipped
        - Control email recipients (followers excluded by default)
        - Manual CC selection option
        - Customizable email templates
        
        Important:
        - Followers do NOT receive automatic emails
        - Only specified recipients receive emails
        - Followers can be manually added to CC if needed
    """,
    'category': 'Sales/Sales',
    'author': 'Ksolves',
    'website': '',
    'depends': ['sale', 'mail', 'stock', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'data/email_templates.xml',
        'views/ks_automail_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

