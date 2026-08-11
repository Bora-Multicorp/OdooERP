# -*- coding: utf-8 -*-
{
    "name": "Line Discount Amount",
    "summary": 'Sales/Purchase/Accounting',
    "description": """
Line Discount Amount
====================

This module adds a discount amount field to transaction lines.

Features:
- Discount Amount on Sales Order Lines
- Discount Amount on Purchase Order Lines
- Discount Amount on Customer Invoice Lines
- Discount Amount on Vendor Bill Lines
- Synchronize discount amount with the standard discount percentage
""",
    "author": "SunArc Technologies Private Limited",
    "website": "https://sunarctechnologies.com/",
    "category": "Sales/Purchase/Accounting",
    "version": "1.0",
    "depends": ["sale_management", "purchase", "account"],
    "data": [
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
