from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    responsible_person_ids = fields.Many2many(
        comodel_name='res.partner',
        string='Responsible Users',
        help='Select the people responsible for this warehouse'
    )

    email = fields.Char(
        string='Email',
        help='General contact email for the warehouse'
    )
    warehouse_type = fields.Selection(
        selection=[
            ('internal', 'Internal'),
            ('3pl', '3PL')
        ],
        string='Warehouse Type',
        default='internal',
        required=True,
        help='Specify whether this warehouse is Internal or managed by a 3PL provider.'
    )