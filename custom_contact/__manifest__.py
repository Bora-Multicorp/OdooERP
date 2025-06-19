# -*- coding: utf-8 -*-
{
    'name': "custom_contact",

    'summary': "Custom Contact",
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'contacts', 'account','accountant', 'purchase'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/custom_partner.xml',
        'views/master_view.xml',
        'data/master_data.xml',
    ],

}
