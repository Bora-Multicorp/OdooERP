# -*- coding: utf-8 -*-

from odoo import fields, models


class KsWarehouseData(models.Model):
    _name = "ks.warehouse.data"
    _description = "Warehouse Data (Pune, Delhi, Karnal)"
    _order = "date desc, id desc"

    warehouse_type = fields.Selection(
        [
            ("pune", "Pune"),
            ("delhi", "Delhi"),
            ("karnal", "Karnal"),
        ],
        string="Warehouse",
        required=True,
        index=True,
    )
    sr_no = fields.Char(string="SR NO.", default="NA", copy=False)
    grn_no = fields.Char(string="GRN No.", default="NA", copy=False)
    date = fields.Date(string="Date", copy=False)
    awb = fields.Char(string="AWB", default="NA", copy=False)
    order_id = fields.Char(string="Order ID", default="NA", copy=False)
    invoice_no = fields.Char(string="Invoice No.", default="NA", copy=False)
    model_name = fields.Char(string="Model", default="NA", copy=False)
    qty = fields.Float(string="Quantity", copy=False)
    rate = fields.Float(string="Rate", copy=False)
    i_w = fields.Char(string="I/W", default="NA", copy=False)
    person = fields.Char(string="Person", default="NA", copy=False)
    delivered = fields.Char(
        string="Delivery Status",
        default="NA",
        copy=False,
        help="Delivered (Pune) / Company Delivered (Delhi, Karnal).",
    )
    diff = fields.Float(string="Diff", copy=False)
