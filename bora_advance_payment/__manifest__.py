# -*- coding: utf-8 -*-
{
    'name': "bora_advance_payment",

    'summary': "Advance payment",

    'description': """
Advance payment
    """,

    'author': "Bora",
    'website': "",

    'category': 'Sale',
    'version': '0.1',

    'depends': ['base', 'sale', 'account'],

    'data': [
        # 'security/ir.model.access.csv',
        'views/inherit_sale_order.xml',
        'views/inherit_account_payment.xml'
    ],

    'application': True,
    'installable': True,
    'license': 'Other proprietary'

}

