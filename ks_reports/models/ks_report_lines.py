# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AdvanceSheetLine(models.TransientModel):
    _name = 'ks.advance.sheet.line'
    _description = 'Advance Sheet Report Line (same format as print)'

    sr_no = fields.Integer('Sr No.')
    party_name = fields.Char('Party Name')
    payment_received = fields.Float('Payment Received', digits='Account')
    stock_dispatched_amount = fields.Float('Stock Dispatched Amount', digits='Account')
    balance_available = fields.Float('Balance Available', digits='Account')
    balance_display = fields.Char('Balance', compute='_compute_balance_display')

    @api.depends('payment_received', 'stock_dispatched_amount', 'balance_available')
    def _compute_balance_display(self):
        for r in self:
            if r.payment_received == 0 or r.stock_dispatched_amount == 0:
                r.balance_display = 'NA'
            else:
                r.balance_display = '%.2f' % (r.balance_available or 0)


class PartWiseReportLine(models.TransientModel):
    _name = 'ks.part.wise.report.line'
    _description = 'Part Wise All Data Report Line (same format as print)'

    sn = fields.Integer('SN')
    pi_no = fields.Char('PI No.')
    party_name = fields.Char('Party Name')
    products = fields.Char('Products')
    total_pi_quantity = fields.Float('Total PI Quantity', digits='Product Unit of Measure')
    total_pi_amount = fields.Float('Total PI Amount', digits='Account')
    dispatched_quantity = fields.Float('Dispatched Quantity', digits='Product Unit of Measure')
    dispatched_amount = fields.Float('Dispatched Amount', digits='Account')
    balance_qty = fields.Float('Balance Qty', digits='Product Unit of Measure')
    remaining_amount_against_pi = fields.Float('Remaining Amount Against PI', digits='Account')
    monthly_plan_quantity = fields.Float('Monthly Plan Quantity', digits='Product Unit of Measure')
    monthly_plan_amount = fields.Float('Monthly Plan Amount', digits='Account')
    export_inv_qty_this_month = fields.Float('Export Inv Qty This Month', digits='Product Unit of Measure')
    export_inv_amount_this_month = fields.Float('Export Inv Amount This Month', digits='Account')
    gst = fields.Float('GST', digits='Account')
    deviation_from_plan_1 = fields.Float('Deviation From Plan', digits='Account')
    deviation_from_plan_2 = fields.Float('Deviation From Plan 2', digits='Account')
    net_remaining_qty = fields.Float('Net Remaining Qty', digits='Product Unit of Measure')
    net_remaining_amount = fields.Float('Net Remaining Amount', digits='Account')


class ExchangeGLLine(models.TransientModel):
    _name = 'ks.exchange.gl.line'
    _description = 'Exchange GL Report Line (same format as print)'

    proforma_invoice_no = fields.Char('Proforma Invoice No.')
    proforma_invoice_date = fields.Date('Proforma Invoice Date')
    currency = fields.Char('Currency')
    exchange_rate_pi_date = fields.Float('Exchange Rate on PI Date', digits=(12, 6))
    qty = fields.Float('Qty', digits='Product Unit of Measure')
    total_qty = fields.Float('Total Qty', digits='Product Unit of Measure')
    rate_inr = fields.Float('Rate (INR)', digits='Account')
    pi_amount = fields.Float('PI Amount', digits='Account')
    total_amount = fields.Float('Total Amount', digits='Account')
    commercial_invoice_no = fields.Char('Commercial Invoice No.')
    commercial_invoice_date = fields.Date('Commercial Invoice Date')
    commercial_invoice_amount = fields.Float('Commercial Invoice Amount', digits='Account')
    shipping_bill_no = fields.Char('Shipping Bill No.')
    shipping_bill_date = fields.Date('Shipping Bill Date')
    shipping_bill_value = fields.Float('Shipping Bill Value', digits='Account')
    shipping_bill_exchange_rate = fields.Float('Shipping Bill Exchange', digits=(12, 6))
    shipping_bill_value_inr = fields.Float('Shipping Bill Value INR', digits='Account')
    total_amount_received = fields.Float('Total Amount Received', digits='Account')
    bank_charges = fields.Float('Bank Charges', digits='Account')
    net_amount_received = fields.Float('Net Amount Received', digits='Account')
    exchange_rate_remittance_date = fields.Float('Exchange Rate on Remittance Date', digits=(12, 6))
    payment_received_inr = fields.Float('Payment Received INR', digits='Account')
    exchange_gain_loss = fields.Float('Exchange Gain or Loss', digits='Account')
