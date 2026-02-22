# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PoManifestLine(models.Model):
    _name = 'po.manifest.line'
    _description = 'Purchase Order Manifest Line'
    _order = 'id desc'

    order_id = fields.Many2one(
        comodel_name='purchase.order',
        string="Purchase Order",
        required=True,
        ondelete='cascade',
        index=True,
    )
    
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        index=True,
    )
    
    sku = fields.Char(
        string="SKU",
        required=True,
        index=True,
    )
    
    imei = fields.Char(
        string="IMEI",
        required=True,
        index=True,
    )
    
    imei2 = fields.Char(
        string="IMEI 2",
        index=True,
    )
    
    qty = fields.Integer(
        string="Quantity",
        default=1,
    )
    
    is_received = fields.Boolean(
        string="Received",
        default=False,
        help="Marked as True when this IMEI has been validated during receipt.",
    )
    
    received_move_line_id = fields.Many2one(
        comodel_name='stock.move.line',
        string="Received Move Line",
        help="The stock move line where this IMEI was received.",
    )

    _sql_constraints = [
        ('imei_order_unique', 'UNIQUE(order_id, imei)', 
         'IMEI must be unique per Purchase Order!'),
    ]

    @api.depends('sku', 'imei')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.sku} - {record.imei}"

