# -*- coding: utf-8 -*-
{
    'name': "dubai_sale",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm', 'purchase', 'sale', 'sale_stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/procurement_team_views.xml',
        'views/pi_unlock_approvers.xml',
        'views/sale_order_unlock.xml',
        'views/unlock_button_action_inherited.xml',
        # 'data/translation.xml'
    ],
    # only loaded in demonstration mode
    # 'demo': [
    #     'demo/demo.xml',
    # ],
    'application': True,
    'installable': True,
    'license': 'Other proprietary',
}

