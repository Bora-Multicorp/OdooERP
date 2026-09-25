# -*- coding: utf-8 -*-
{
    'name': 'Bora E-Commerce & Marketplace',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'summary': 'E-Com & Marketplace master configuration, dynamic PO fields, and E-Commerce tracking',
    'description': """
Bora E-Commerce & Marketplace
=============================
Key Features:
1. E-Commerce PO Filter and Tracking:
   - Custom filter and search option in Purchase Order list/tree and search views.
   - Enables users to view, monitor, and track all E-Commerce Purchase Orders and their current status.

2. E-Com & Marketplace Fields on Purchase Order:
   - Custom Many2one field 'E-Com' (bora.ecom.master) on Purchase Order form.
   - Identifies whether the PO is an E-Commerce PO based on selected category.
   - Custom Many2one field 'Marketplace' (bora.marketplace.master) on Purchase Order form.
   - Dynamic visibility: Marketplace remains hidden by default and becomes visible below E-Com only when 'E-Commerce' is selected.
   - Automatically hides and clears Marketplace when category changes to Domestic, Export, or another non-E-Commerce value.
   - Existing PO approval workflow and access rights are completely unaffected.

3. Master Data Configurations (Purchase > Configuration):
   - E-Com Master: Maintain business categories such as Domestic, E-Commerce, Export, and future categories.
   - Marketplace Master: Maintain marketplaces such as Amazon, Flipkart, and future marketplaces.
   - Preloaded default master data with secure access control for authorized users.
    """,
    'author': 'Bora',
    'depends': [
        'purchase',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ecom_master_data.xml',
        'views/ecom_master_views.xml',
        'views/marketplace_master_views.xml',
        'views/purchase_order_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
