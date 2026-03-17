{
    "name": "KS E-com Purchase Import",
    "summary": "Import purchase orders from e-commerce XLSX files",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "author": "Ksolves",
    "website": "https://www.ksolves.com",
    "license": "LGPL-3",
    "depends": ["purchase", "base_import", "ks_sale_order", "stock", "bus", "account"],
    "external_dependencies": {"python": ["openpyxl"]},
    "data": [
        "security/ir.model.access.csv",
        "data/ks_po_warehouse_tracking_data.xml",
        "wizard/po_import_wizard_views.xml",
        "wizard/po_receipt_import_wizard_views.xml",
        "wizard/po_refund_import_wizard_views.xml",
        "views/purchase_order_views.xml",
        "views/stock_picking_views.xml",
        "views/ks_warehouse_data_views.xml",
        "views/ks_po_warehouse_tracking_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ks_ecom_purchase/static/src/js/ecom_import_menu.js",
            "ks_ecom_purchase/static/src/xml/ecom_import_menu.xml",
        ],
    },
    "installable": True,
    "application": False,
}

