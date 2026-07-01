# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class AdvanceSheetLine(models.TransientModel):
    _name = 'ks.advance.sheet.line'
    _description = 'Advance Sheet Report Line (same format as print)'

    sr_no = fields.Integer('Sr No.')
    commercial_partner_id = fields.Many2one('res.partner', string='Party (for filter)', help='Used to filter XLSX by selected rows.')
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

    def action_download_xlsx(self):
        if not self:
            raise UserError('Please select one or more rows in the list to download.')
        report_model = self.env['ks.part.wise.all.data.report']
        partner_ids = self.mapped('commercial_partner_id').ids
        sale_order_ids = []
        if partner_ids:
            orders = self.env['sale.order'].search([
                ('partner_id.commercial_partner_id', 'in', partner_ids),
                ('state', '!=', 'cancel'),
            ])
            sale_order_ids = orders.ids if orders else []
        file_content = report_model.generate_advance_sheet_xlsx_report(sale_order_ids=sale_order_ids or None)
        attachment = self.env['ir.attachment'].create({
            'name': 'Advance_Sheet_Report.xlsx',
            'type': 'binary',
            'datas': file_content,
            'res_model': self._name,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }


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
    unit_price = fields.Float('Unit Price', digits='Account')
    gst = fields.Float('GST', digits='Account')
    deviation_from_plan_1 = fields.Float('Deviation From Plan', digits='Product Unit of Measure', compute='_compute_deviation_and_net', store=False)
    deviation_from_plan_2 = fields.Float('Deviation From Plan Amount', digits='Account', compute='_compute_deviation_and_net', store=False)
    net_remaining_qty = fields.Float('Net Remaining Qty', digits='Product Unit of Measure')
    net_remaining_amount = fields.Float('Net Remaining Amount', digits='Account')

    @api.depends('monthly_plan_quantity', 'export_inv_qty_this_month', 'unit_price')
    def _compute_deviation_and_net(self):
        for r in self:
            # DEVIATION FROM PLAN = Monthly Plan Quantity - EXPORT INVOICE QUANTITY FOR THIS MONTH
            r.deviation_from_plan_1 = (r.monthly_plan_quantity or 0.0) - (r.export_inv_qty_this_month or 0.0)
            # DEVIATION FROM PLAN AMOUNT = DEVIATION FROM PLAN * UNIT PRICE
            r.deviation_from_plan_2 = r.deviation_from_plan_1 * (r.unit_price or 0.0)

    def action_download_xlsx(self):
        if not self:
            raise UserError('Please select one or more rows in the list to download.')
        report_model = self.env['ks.part.wise.all.data.report']
        pi_nos = self.mapped('pi_no')
        sale_order_ids = []
        if pi_nos:
            orders = self.env['sale.order'].search([
                ('name', 'in', list(pi_nos)),
                ('state', 'in', ['sale', 'done']),
            ])
            sale_order_ids = orders.ids if orders else []
        file_content = report_model.generate_xlsx_report(
            sale_order_ids=sale_order_ids or None,
            report_lines=self,
        )
        attachment = self.env['ir.attachment'].create({
            'name': 'Part_Wise_All_Data.xlsx',
            'type': 'binary',
            'datas': file_content,
            'res_model': self._name,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }


class ExchangeGLLine(models.TransientModel):
    _name = 'ks.exchange.gl.line'
    _description = 'Exchange GL Report Line (same format as print)'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        domain=[('move_type', 'in', ['out_invoice', 'out_refund'])],
        help='Invoice used to sync Shipping Bill No, Exchange Rate SB and Payment Received INR from sb.brc.master and sale.order',
    )
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
    shipping_bill_no = fields.Char(
        'Shipping Bill ( SB) No.',
        compute='_compute_exchange_data',
        store=False,
        readonly=False,
    )
    shipping_bill_date = fields.Date('Shipping Bill Date')
    shipping_bill_value = fields.Float('Shipping Bill Value USD/ AED/HKD', digits='Account')
    shipping_bill_exchange_rate = fields.Float(
        'Exchange Rate SB',
        digits=(12, 6),
        compute='_compute_exchange_data',
        store=False,
        readonly=False,
    )
    shipping_bill_value_inr = fields.Float('Shipping Bill Value INR', digits='Account')
    total_amount_received = fields.Float('Total Amount Received( TT Amount) USD/ AED/HKD', digits='Account')
    bank_charges = fields.Float('Bnak Charges, Currency Charges USD/ AED/HKD', digits='Account')
    net_amount_received = fields.Float('Net Amount Recevied USD/ AED/HKD', digits='Account')
    exchange_rate_remittance_date = fields.Float('Exchange Rate on Remittance Date', digits=(12, 6))
    payment_received_inr = fields.Float(
        'Payment Received INR',
        digits='Account',
        compute='_compute_exchange_data',
        store=False,
        readonly=False,
    )
    exchange_gain_loss = fields.Float('Exchange Gain or Loss', digits='Account')

    @api.depends('invoice_id')
    def _compute_exchange_data(self):
        company = self.env.company
        company_currency = company.currency_id
        sb_master_model = self.env.get('sb.brc.master')

        for line in self:
            sb_no_val = ''
            sb_rate_val = 0.0
            payment_received_inr_val = 0.0

            if line.invoice_id:
                # Shipping Bill No & Exchange Rate SB: from sb.brc.master (match by invoice_id)
                if sb_master_model is not None:
                    sb_master = sb_master_model.search([
                        ('invoice_id', '=', line.invoice_id.id),
                    ], limit=1)
                    if sb_master:
                        sb_no_val = sb_master.sb_no or ''
                        sb_rate_val = getattr(sb_master, 'sb_ex_rate', None) or getattr(sb_master, 'sb_rate', None) or 0.0

                # PAYMENT RECEIVED INR: from sale.order linked via invoice_origin (if no SO, keep 0)
                origin = (line.invoice_id.invoice_origin or '').strip()
                if origin:
                    sale_order = self.env['sale.order'].search([
                        ('name', '=', origin),
                        ('state', '!=', 'cancel'),
                    ], limit=1)
                    if sale_order:
                        adv = getattr(sale_order, 'ks_advance_payment_amount', None) or 0.0
                        inv_pay = getattr(sale_order, 'total_invoice_payment_received', None) or 0.0
                        order_payment = adv + inv_pay
                        if order_payment and sale_order.currency_id:
                            order_date = (
                                sale_order.date_order.date()
                                if sale_order.date_order
                                else fields.Date.context_today(self)
                            )
                            try:
                                payment_received_inr_val = sale_order.currency_id._convert(
                                    order_payment,
                                    company_currency,
                                    company,
                                    order_date,
                                )
                            except Exception:
                                payment_received_inr_val = order_payment

            line.shipping_bill_no = sb_no_val
            line.shipping_bill_exchange_rate = sb_rate_val
            line.payment_received_inr = payment_received_inr_val

    def action_download_xlsx(self):
        if not self:
            raise UserError('Please select one or more rows in the list to download.')
        report_model = self.env['ks.part.wise.all.data.report']
        pi_nos = self.mapped('proforma_invoice_no')
        sale_order_ids = []
        if pi_nos:
            orders = self.env['sale.order'].search([
                ('name', 'in', list(pi_nos)),
                ('state', 'in', ['sale', 'done']),
            ])
            sale_order_ids = orders.ids if orders else []
        file_content = report_model.generate_exchange_gl_xlsx_report(sale_order_ids=sale_order_ids or None)
        attachment = self.env['ir.attachment'].create({
            'name': 'Exchange_GL_Report.xlsx',
            'type': 'binary',
            'datas': file_content,
            'res_model': self._name,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s?download=true' % attachment.id,
            'target': 'self',
        }
