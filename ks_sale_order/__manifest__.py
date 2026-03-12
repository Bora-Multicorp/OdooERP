# -*- coding: utf-8 -*-
{
    'name': "KS Sale Order - Stock Validation",
    'summary': "Block sales order lines when product stock is insufficient and notify procurement team",
    'description': """
KS Sale Order - Stock Validation
================================

This module enforces stock availability checks when adding products to sales orders.

Features:
---------
* Validates product quantity against physically available stock for the sales order's company
* **Blocks** users from adding products when stock is zero or insufficient
* Shows a clear error message explaining the stock shortage
* Automatically sends email notifications to the Procurement Team
* Procurement Team is configurable per company in Settings

The module includes:
* Stock availability validation on sale order line create/write
* Error blocking with descriptive UserError messages
* Professional email template for procurement notifications
* Settings page to configure Procurement Team members per company
* Direct link to the sales order in the notification email

Configuration:
--------------
1. Go to Sales > Configuration > Settings
2. Scroll to "Stock Availability Validation" section
3. Add users to the Procurement Team for the current company
4. These users will receive email notifications about stock shortages
    """,
    'author': "Ksolves",
    'website': "https://www.ksolves.com",
    'category': 'Sales/Sales',
    'version': '18.0.1.0.0',
    'depends': ['sale_stock', 'mail', 'ks_sale_approval', 'purchase', 'ks_automail', 'ks_payment_access_control', 'ks_sale_advance_payment', 'ks_doc', 'product', 'l10n_in'],
    'data': [
        'security/ir.model.access.csv',
        'data/hide_products_menu.xml',
        'data/mail_template_data.xml',
        'views/res_config_settings_views.xml',
        'views/res_company_views.xml',
        'views/res_bank_views.xml',
        'views/product_template_views.xml',
        'views/sale_order_views.xml',
        'views/tax_fields_readonly_views.xml',
        'views/product_pricelist_item_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

