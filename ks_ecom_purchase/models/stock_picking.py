# -*- coding: utf-8 -*-

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ks_ecom_po_reciept = fields.Boolean(
        string="E-com PO Receipt",
        default=False,
        copy=False,
        help="True when this receipt was generated from an E-com imported Purchase Order.",
    )
    ks_ecom_order_id = fields.Char(
        string="Order ID",
        copy=False,
        help="E-com Order ID; set when receipt is updated via Import XLSX Receipt Data.",
    )
    is_ecom_updated = fields.Boolean(
        string="E-com Updated",
        default=False,
        copy=False,
        help="True when this receipt has been updated via Excel import (Import XLSX Receipt Data).",
    )
    ks_ecom_info_ids = fields.One2many(
        "ks.ecom.picking.info",
        "picking_id",
        string="Imported E-com Information",
        copy=False,
    )
    is_ecom_refund = fields.Boolean(
        string="Is E-com Refund",
        default=False,
        copy=False,
        help="True when this picking was created through the Import XLSX Refund Data process.",
    )


class KsEcomPickingInfo(models.Model):
    _name = "ks.ecom.picking.info"
    _description = "E-com Picking Imported Information"
    _order = "id"

    picking_id = fields.Many2one("stock.picking", required=True, ondelete="cascade")
    field_key = fields.Char(string="Field", required=True)
    field_value = fields.Char(string="Value")
