# -*- coding: utf-8 -*-
{
    'name': 'KS Payment Tracker',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Payment tracker for Purchase Orders – submit POs for payment approval (LO-002 format)',
    'description': """
        Payment Tracker for Purchase Orders
        ===================================
        - Menu: Payment Tracker (list of all open POs whose payment is pending).
        - On Purchase Order list view: button "Submit for Payment Approval".
        - Select multiple POs and click the button to create records in the payment tracker.
        - Tracker fields follow report source LO-002.xlsx (SN, PO No, Sales Person, From, Vendor,
          Invoice No, E-Invoice, Model, F/A, Qty, Rate, Amount, TDS, Amt To Be Paid, Stock Status,
          Purpose, Purchase Date, Transporter, At Warehouse, Approved).
    """,
    'author': 'Ksolves',
    'website': '',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/ks_payment_tracker_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
