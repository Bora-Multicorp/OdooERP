# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class KsWarehouseInsurance(models.Model):
    _name = 'ks.warehouse.insurance'
    _description = 'Warehouse Insurance & Value Tolerance Management'
    _order = 'warehouse_id'

    # Warehouse
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        help='Select warehouse name from stock.warehouse'
    )

    # Insurance Amount
    insurance_amount = fields.Float(
        string='Insurance Amount',
        required=True,
        digits=(16, 2),
        help='Manually entered insurance amount'
    )

    # Total Value in Warehouse
    total_value = fields.Float(
        string='Total Value in Warehouse',
        required=True,
        digits=(16, 2),
        help='Manually entered total stock value of warehouse'
    )

    # Tolerance Percentage
    tolerance = fields.Float(
        string='Tolerance Percentage',
        required=True,
        digits=(16, 2),
        help='Tolerance percentage entered manually'
    )

    # Value Over or Under (Computed Field)
    value_over_under = fields.Float(
        string='Value Over or Under',
        compute='_compute_value_over_under',
        store=True,
        digits=(16, 2),
        help='Calculated value based on tolerance. Formula: Total Value * (Tolerance / 100)'
    )

    @api.depends('total_value', 'tolerance')
    def _compute_value_over_under(self):
        """
        Calculate Value Over or Under based on tolerance percentage
        Formula: Total Value in Warehouse * (Tolerance / 100)
        """
        for record in self:
            if record.total_value and record.tolerance:
                record.value_over_under = record.total_value * (record.tolerance / 100)
            else:
                record.value_over_under = 0.0

