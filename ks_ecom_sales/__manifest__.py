{
    "name": "KS E-com Sales Import",
    "summary": "Import sales orders from e-commerce XLSX files",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "author": "Ksolves",
    "website": "https://www.ksolves.com",
    "license": "LGPL-3",
    "depends": ["sale_management", "base_import", "stock", "bus", "account", "ks_contact"],
    "external_dependencies": {"python": ["openpyxl"]},
    "data": [
        "security/ir.model.access.csv",
        "wizard/so_import_wizard_views.xml",
        "wizard/so_delivery_import_wizard_views.xml",
        "views/sale_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "ks_ecom_sales/static/src/js/ecom_sale_import_menu.js",
            "ks_ecom_sales/static/src/xml/ecom_sale_import_menu.xml",
        ],
    },
    "installable": True,
    "application": False,
}
