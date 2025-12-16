# -*- coding: utf-8 -*-
{
    'name' : 'Product Multi Images',
    'version' : '18.0.1.0.0',
    'category': 'eCommerce',
    'summary': 'Multi-image upload option (up to 5), brand selection, and image display on sale order report',
    'author': 'Hi Spark Solutions',
    'company': 'Hi Spark Solutions',
    'maintainer': 'Hi Spark Solutions',
    'website': 'https://www.hisparksolutions.com/',
    'description': """ Enhance your sales workflow with multi-image upload capability (up to 5 images), dynamic brand selection, and automatic image display on sale order reports—perfect for showcasing products visually and professionally. """,
    'depends': ['sale', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_view.xml',
        'report/inherit_ir_actions_report_templates.xml',
    ],
    'images': [
        'static/description/banner.jpg',
    ],
    'assets': {},
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}

