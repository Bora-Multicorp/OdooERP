# -*- coding: utf-8 -*-
{
    'name': 'KS Sale Documents',
    'version': '18.0.1.0.0',
    'summary': 'Upload and send sale order documents to customers',
    'description': """
        KS Sale Documents Module
        ========================
        
        This module allows you to:
        - Upload multiple documents to a Sale Order (Airways bill, Packing list, etc.)
        - Categorize documents by type
        - Send all documents as a ZIP file to the customer via email
        
        Document Types Supported:
        - Airways Bill
        - Packing List
        - Transport Bill
        - EVR (Export Verification Report)
        - Export Bill
        - Other Documents
    """,
    'category': 'Sales/Sales',
    'author': 'Ksolves',
    'website': '',
    'depends': ['sale', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/sale_document_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

