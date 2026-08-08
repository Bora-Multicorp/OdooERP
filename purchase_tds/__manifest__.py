# -*- coding: utf-8 -*-
{
    "name": "Purchase TDS",
    "summary": 'Apply and manage Indian TDS (Withholding Tax) on Purchase Orders',
    "description": """
Purchase TDS for India Localization
====================================
This module extends Indian withholding tax (TDS) capabilities to Purchase Orders:
* Adds a TDS wizard on Purchase Order form views.
* Computes and applies TDS taxes to Purchase Order lines.
* Automatically transfers applied TDS taxes to Vendor Bills upon creation.
    """,
    "author": "SunArc Technologies Private Limited",
    "website": "https://sunarctechnologies.com/",
    "category": "Purchase",
    "version": "1.0",
    "depends": ["product", "purchase", "l10n_in_withholding"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/purchase_tds_wizard_views.xml",
        "views/purchase_tds_views.xml",
        "views/purchase_views.xml"
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
