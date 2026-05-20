{
    "name": "KS Dual Price (Excl/Incl GST)",
    "summary": "Show Unit Price Excl. GST and Incl. GST on Sale Orders, Purchase Orders, Invoices and Bills",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "depends": ["sale_management", "purchase", "account", "ks_purchase_approval"],
    "data": [
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
    ],
    "license": "AGPL-3",
    "installable": True,
}
