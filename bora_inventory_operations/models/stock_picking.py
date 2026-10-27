# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pickup_date = fields.Datetime(
        string='Pick-Up Date',
        copy=False,
    )
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Carrier/Transporter',
        check_company=True,
    )
    carrier_tracking_ref = fields.Char(
        string='Tracking Reference/Docket Number',
        copy=False,
    )

    # 1(c) Docket LR Copy (document upload with preview)
    docket_lr_copy = fields.Many2many(
        'ir.attachment',
        'stock_picking_docket_lr_rel',
        'picking_id',
        'attachment_id',
        string='Docket LR Copy',
    )
    # 3(c) Amount (float)
    amount = fields.Float(
        string='Amount',
    )
    # 2(c) Additional details (html)
    additional_details = fields.Html(
        string='Additional details',
    )

    # Inspection at Pick-up point: 1(i) Fresh/Activated
    fresh_activated = fields.Selection(
        [
            ('matched', 'Matched'),
            ('not_matched', 'Not Matched'),
        ],
        string='Fresh/Activated',
    )
    fresh_activated_remark = fields.Text(
        string='Remark',
    )

    # Inspection at Pick-up point: 2(i) Loose/Master
    loose_master = fields.Selection(
        [
            ('matched', 'Matched'),
            ('not_matched', 'Not Matched'),
        ],
        string='Loose/Master',
    )
    loose_master_remark = fields.Text(
        string='Remark',
    )

    # Inspection at Pick-up point: 3(i) Inspection Condition
    inspection_condition = fields.Selection(
        [
            ('neat_and_clean', 'Neat and Clean'),
            ('damage', 'Damage'),
            ('box_press', 'Box Press'),
        ],
        string='Inspection Condition',
    )
    inspection_condition_remark = fields.Text(
        string='Remark',
    )

    # Documents Section: 1(d) E- Invoice
    e_invoice = fields.Many2many(
        'ir.attachment',
        'stock_picking_e_invoice_rel',
        'picking_id',
        'attachment_id',
        string='E- Invoice',
    )
    # Documents Section: 2(d) E-way bill
    eway_bill = fields.Many2many(
        'ir.attachment',
        'stock_picking_eway_bill_rel',
        'picking_id',
        'attachment_id',
        string='E-way bill',
    )
    # Documents Section: 3(d) IMEI sheet
    imei_sheet = fields.Many2many(
        'ir.attachment',
        'stock_picking_imei_sheet_rel',
        'picking_id',
        'attachment_id',
        string='IMEI sheet',
    )

    @api.constrains('pickup_date', 'carrier_id', 'carrier_tracking_ref', 'fresh_activated', 'loose_master', 'inspection_condition')
    def _check_pickup_details_mandatory_fields(self):
        for picking in self:
            if picking.pickup_date:
                if not picking.carrier_id:
                    raise ValidationError(_("Carrier/Transporter is required when Pick-Up Date is set."))
                if not picking.carrier_tracking_ref:
                    raise ValidationError(_("Tracking Reference/Docket Number is required when Pick-Up Date is set."))
                if not picking.fresh_activated:
                    raise ValidationError(_("Fresh/Activated is required when Pick-Up Date is set."))
                if not picking.loose_master:
                    raise ValidationError(_("Loose/Master is required when Pick-Up Date is set."))
                if not picking.inspection_condition:
                    raise ValidationError(_("Inspection Condition is required when Pick-Up Date is set."))
