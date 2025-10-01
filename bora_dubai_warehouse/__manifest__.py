{
    'name': 'Warehouse configuration Email Notification',
    'version': '1.0',
    'summary': 'Adds responsible persons (Many2many) and email field to warehouses',
    'category': 'Inventory/Inventory',
    'license': 'LGPL-3',
    'depends': [
        'stock',  # Required because we are inheriting stock.warehouse
        'contacts',# Required because we use res.partner
        'sale',
        'purchase',
        'account',
        'sale_management'
    ],
    'data': [
        'data/freezone_trade.xml',
        # 'data/purchase_order_confirm.xml',
        'data/full_payment_email.xml',
        'views/stock_warehouse.xml',
        'views/sale_order.xml',
        # 'views/purchase_order.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
