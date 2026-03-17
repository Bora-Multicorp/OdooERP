# -*- coding: utf-8 -*-
{
    'name': 'KS Accounting',
    'version': '18.0.1.0.0',
    'summary': 'Warehouse Insurance & Value Tolerance Management',
    'description': """
        KS Accounting Module
        ====================
        
        This module manages warehouse insurance and value tolerance calculations.
        
        Features:
        - Warehouse Insurance Management
        - Value Tolerance Calculations
        - Automatic calculation of value over/under based on tolerance percentage
        
        Model: ks.warehouse.insurance
        - Links to stock.warehouse
        - Tracks insurance amount and total warehouse value
        - Calculates value over/under based on tolerance percentage
    """,
    'category': 'Accounting/Accounting',
    'author': 'Ksolves',
    'website': '',
    'depends': ['stock', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/ks_warehouse_insurance_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

