# -*- coding: utf-8 -*-
{
    'name': "KS E-Commerce Purchase IMEI Management",
    'summary': "Upload manifest CSV with IMEI data and validate receipts against expected IMEIs",
    'description': """
        This module provides functionality for managing IMEI tracking in purchase orders:
        
        Features:
        =========
        
        1. Purchase Order Manifest Upload:
           - Upload CSV manifest files with SKU, IMEI, IMEI2, Qty
           - Auto-map CSV lines to PO lines by SKU matching
           - Store all IMEI data in po.manifest.line model
           - View all manifest lines via smart button on PO
        
        2. Receipt IMEI Validation:
           - Scan/enter IMEI and IMEI2 on stock move lines
           - IMEI fields only visible for Mobile/Phone category products
           - Validate scanned IMEIs against expected manifest data
           - Block validation if mismatches found
           - Show detailed mismatch report wizard
        
        3. IMEI On Hold Management:
           - Mismatched items automatically moved to On Hold location
           - Items in On Hold are blocked from stock availability
           - Manual resolution workflow to release items
           - Configurable On Hold location in settings
        
        CSV Format:
        ===========
        SKU,IMEI,IMEI2,Qty
        PHONE-001,123456789012345,123456789012346,1
        PHONE-002,234567890123456,,1
    """,
    'author': "Ksolves Private Limited",
    'website': "https://www.ksolves.com/",
    'category': 'Inventory/Purchase',
    'version': '18.0.2.0.0',
    'license': 'Other proprietary',
    
    'depends': ['purchase_stock', 'stock', 'barcodes','ks_product_master'],
    
    'data': [
        'security/ir.model.access.csv',
        'data/imei_on_hold_location.xml',
        'data/breached_purchase_order_cron.xml',
        'views/po_manifest_line_views.xml',
        'views/purchase_order_views.xml',
        # 'views/stock_move_line_views.xml',
        'views/res_partner_view.xml',
        'views/res_config_settings_views.xml',
        'wizards/manifest_upload_wizard_views.xml',
        'wizards/imei_validation_wizard_views.xml',

    ],
    
    'installable': True,
    'application': False,
    'auto_install': False,
}
