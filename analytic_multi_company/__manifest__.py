# -*- coding: utf-8 -*-

{
    "name": "Analytic Account Multi-Company",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Make analytic accounts company-independent for multi-company environments",
    "description": """
        This module makes Odoo's analytic accounts fully company-independent:
        
        * Removes company constraints from analytic accounts
        * Allows analytic accounts to be shared across all companies
        * Updates all related features to work with company-independent analytic accounts
        * Ensures cross-company consistency in accounting, expenses, projects, timesheets, sales, purchases, and stock moves
    """,
    "author": "Ksolves",
    "website": "https://www.ksolves.com",
    "license": "LGPL-3",
    "depends": [
        "analytic",
        "account",
    ],
    "data": [
        "views/analytic_account_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}


