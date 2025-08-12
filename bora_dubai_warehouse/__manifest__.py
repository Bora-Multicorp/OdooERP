{
    'name': 'Warehouse configurationEmail Notification',
    'version': '1.0',
    'summary': 'Adds responsible persons (Many2many) and email field to warehouses', 
    'category': 'Inventory/Inventory',
    'license': 'LGPL-3',
    'depends': [
        'stock',  # Required because we are inheriting stock.warehouse
        'contacts',# Required because we use res.partner
        'sale'
    ],
    'data': [
        'data/freezone_trade.xml',
        'views/stock_warehouse.xml',
        'views/sale_order.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
