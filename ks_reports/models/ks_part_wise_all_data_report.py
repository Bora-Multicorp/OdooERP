# -*- coding: utf-8 -*-

import io
import base64
import re
from datetime import date
from odoo import models, api, fields
from odoo.exceptions import UserError
try:
    import xlsxwriter
except ImportError:
    raise UserError('Please install xlsxwriter: pip install xlsxwriter')


def _to_company_currency(from_currency, amount, company_currency, company, date, env_ref):
    """Convert amount from from_currency to company_currency; no-op if same currency."""
    if not amount:
        return 0.0
    if from_currency == company_currency:
        return amount
    try:
        return from_currency._convert(amount, company_currency, company, date or fields.Date.context_today(env_ref))
    except Exception:
        return amount


def _payment_to_company_currency(payment, amount, company_currency, company, env_ref):
    """Convert payment amount to company currency."""
    if not amount:
        return 0.0
    if payment.currency_id == company_currency:
        return amount
    try:
        return payment.currency_id._convert(
            amount, company_currency, company,
            payment.date or fields.Date.context_today(env_ref)
        )
    except Exception:
        return amount


class PartWiseAllDataReport(models.TransientModel):
    _name = 'ks.part.wise.all.data.report'
    _description = 'Part Wise All Data Report'

    file = fields.Binary(string='XLSX File', attachment=True)
    filename = fields.Char(string='Filename', default='Part_Wise_All_Data.xlsx')

    @api.model
    def generate_xlsx_report(self, sale_order_ids=None):
        """
        Generate XLSX report "SUMMARY FOR NEW ORDER" with Sale Order data.
        Layout: Month, title, TILL DATE; green header with SN, PI NO., PARTY NAME, PRODUCTS,
        quantities/amounts, DISPATCH AMOUNT, BALANCE QTY, deviation, net remaining; TOTAL footer.
        Product-wise display (each product on separate row).
        If sale_order_ids is provided, only those sale orders are included; otherwise all confirmed.
        Returns base64 encoded file content.
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        num_cols = 19
        # Green header with bold WHITE text (as per screenshot)
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#2E7D32',  # Dark green
            'font_color': '#FFFFFF',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        title_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'font_size': 14,
        })
        till_date_format = workbook.add_format({
            'bold': True,
            'align': 'right',
        })
        data_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        number_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'right',
            'num_format': '#,##0.00',
        })
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8F5E9',
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'align': 'right',
        })
        total_label_format = workbook.add_format({
            'bold': True,
            'bg_color': '#E8F5E9',
            'border': 1,
            'valign': 'vcenter',
        })

        # Column widths sized to fit header text in single line (no sub-headers)
        column_widths = [
            8,   # SN
            14,  # PI NO.
            22,  # PARTY NAME
            28,  # PRODUCTS
            22,  # TOTAL PI QUANTITY
            20,  # TOTAL PI AMOUNT
            24,  # DISPATCHED QUANTITY
            22,  # DISPATCHED AMOUNT
            14,  # BALANCE QTY
            32,  # REMAINING AMOUNT AGAINST PI
            24,  # MONTHLY PLAN QUANTITY
            22,  # MONTHLY PLAN AMOUNT
            42,  # EXPORT INVOICE QUANTITY FOR THIS MONTH
            40,  # EXPORT INVOICE AMOUNT FOR THIS MONTH
            10,  # GST
            22,  # DEVIATION FROM PLAN
            28,  # DEVIATION FROM PLAN (2nd col)
            22,  # NET REMAINING QTY
            26,  # NET REMAINING AMOUNT
        ]

        sheet = workbook.add_worksheet('Part Wise All Data')
        for col, w in enumerate(column_widths):
            sheet.set_column(col, col, w)

        # Title block: one line "MONTH SUMMARY FOR NEW ORDER" centered; "TILL DATE dd-mm-yyyy" right-aligned
        till_date = fields.Date.context_today(self)
        till_date_str = till_date.strftime('%d-%m-%Y') if till_date else date.today().strftime('%d-%m-%Y')
        month_name = (till_date or date.today()).strftime('%B').upper()
        sheet.merge_range(0, 0, 0, num_cols - 1, '%s SUMMARY FOR NEW ORDER' % month_name, title_format)
        sheet.merge_range(1, 0, 1, num_cols - 1, 'TILL DATE %s' % till_date_str, title_format)

        # Header row (green, white text) - row 2 (0-indexed)
        main_headers = [
            'SN', 'PI NO.', 'PARTY NAME', 'PRODUCTS',
            'TOTAL PI QUANTITY', 'TOTAL PI AMOUNT', 'DISPATCHED QUANTITY', 'DISPATCHED AMOUNT',
            'BALANCE QTY', 'REMAINING AMOUNT AGAINST PI',
            'MONTHLY PLAN QUANTITY', 'MONTHLY PLAN AMOUNT',
            'EXPORT INVOICE QUANTITY FOR THIS MONTH', 'EXPORT INVOICE AMOUNT FOR THIS MONTH',
            'GST',
            'DEVIATION FROM PLAN', 'DEVIATION FROM PLAN',
            'NET REMAINING QTY', 'NET REMAINING AMOUNT',
        ]
        for col, h in enumerate(main_headers):
            sheet.write(2, col, h, header_format)

        sheet.freeze_panes(3, 0)

        # Get Sale Orders
        if sale_order_ids:
            sale_orders = self.env['sale.order'].browse(sale_order_ids).filtered(
                lambda o: o.state in ['sale', 'done']
            )
        else:
            sale_orders = self.env['sale.order'].search([
                ('state', 'in', ['sale', 'done'])
            ])

        row = 3
        sn = 1
        totals = [0.0] * num_cols

        for order in sale_orders:
            pi_no = order.name or ''
            party_name = order.partner_id.name or ''

            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                total_pi_qty = line.product_uom_qty or 0.0
                total_pi_amount = line.price_subtotal or 0.0
                dispatched_qty = line.qty_delivered or 0.0
                unit_price = line.price_unit or 0.0
                dispatch_amount = dispatched_qty * unit_price
                balance_qty = total_pi_qty - dispatched_qty
                remaining_amount = balance_qty * unit_price
                gst_amount = (line.price_total or 0.0) - (line.price_subtotal or 0.0)
                net_remaining_qty = balance_qty
                net_remaining_amount = remaining_amount

                product_name = line.product_id.name if line.product_id else ''

                sheet.write(row, 0, sn, data_format)
                sheet.write(row, 1, pi_no, data_format)
                sheet.write(row, 2, party_name, data_format)
                sheet.write(row, 3, product_name, data_format)
                sheet.write(row, 4, total_pi_qty, number_format)
                sheet.write(row, 5, total_pi_amount, number_format)
                sheet.write(row, 6, dispatched_qty, number_format)
                sheet.write(row, 7, dispatch_amount, number_format)
                sheet.write(row, 8, balance_qty, number_format)
                sheet.write(row, 9, remaining_amount, number_format)
                sheet.write(row, 10, 0.0, number_format)   # MONTHLY PLAN QUANTITY
                sheet.write(row, 11, 0.0, number_format)  # MONTHLY PLAN AMOUNT
                sheet.write(row, 12, 0.0, number_format)   # EXPORT INVOICE QTY THIS MONTH
                sheet.write(row, 13, 0.0, number_format)   # EXPORT INVOICE AMOUNT THIS MONTH
                sheet.write(row, 14, gst_amount, number_format)
                sheet.write(row, 15, 0.0, number_format)   # DEVIATION Balance of plan
                sheet.write(row, 16, 0.0, number_format)   # DEVIATION qty * Balance Quant
                sheet.write(row, 17, net_remaining_qty, number_format)
                sheet.write(row, 18, net_remaining_amount, number_format)

                # Accumulate totals (cols 4-18 are numeric)
                totals[4] += total_pi_qty
                totals[5] += total_pi_amount
                totals[6] += dispatched_qty
                totals[7] += dispatch_amount
                totals[8] += balance_qty
                totals[9] += remaining_amount
                totals[14] += gst_amount
                totals[17] += net_remaining_qty
                totals[18] += net_remaining_amount

                row += 1
                sn += 1

        # TOTAL row (TOTAL in column B as per screenshot)
        sheet.write(row, 0, '', total_label_format)
        sheet.write(row, 1, 'TOTAL', total_label_format)
        sheet.write(row, 2, '', total_label_format)
        sheet.write(row, 3, '', total_label_format)
        for col in range(4, num_cols):
            sheet.write(row, col, totals[col], total_format)
        row += 1

        workbook.close()
        output.seek(0)
        return base64.b64encode(output.read())

    @api.model
    def generate_002_xlsx_report(self):
        """
        Generate XLSX report 002 with Customer-wise financial and delivery information
        Shows: Party Name, Payment Received, Stock Despatched Amount, Balance Available With Us
        Returns base64 encoded file content
        """
        # Create output in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define header style with yellow background and bold text
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        
        # Define data row format
        data_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        
        # Define number format
        number_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        
        # Define total row format (yellow background)
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        
        # Define column headings
        headers = [
            'SR NO.',
            'PARTY NAME',
            'PAYMENT RECEIVED',
            'STOCK DESPATCHED AMOUNT',
            'BALANCE AVAILABLE WITH US',
        ]
        
        # Set column widths
        column_widths = [
            10,  # SR NO.
            40,  # PARTY NAME
            25,  # PAYMENT RECEIVED
            25,  # STOCK DESPATCHED AMOUNT
            25,  # BALANCE AVAILABLE WITH US
        ]
        
        # Create worksheet
        sheet = workbook.add_worksheet('002 Report')
        
        # Write headers to first row
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        # Apply column widths
        for col, width in enumerate(column_widths):
            sheet.set_column(col, col, width)
        
        # Freeze first row
        sheet.freeze_panes(1, 0)
        
        # Get all confirmed Sale Orders (sale and done states only)
        sale_orders = self.env['sale.order'].search([
            ('state', 'in', ['sale', 'done'])
        ], order='partner_id, name')
        
        # Group data by customer/party - aggregate all sale orders per customer
        customer_data = {}
        
        for order in sale_orders:
            partner = order.partner_id
            partner_key = partner.id
            order_name = order.name or ''
            
            # Initialize customer data if not exists
            if partner_key not in customer_data:
                customer_data[partner_key] = {
                    'party_name': partner.name or '',
                    'payment_received': 0.0,
                    'stock_despatched_amount': 0.0,
                    'payment_ids_seen': set(),  # Track payments to avoid duplicates
                }
            
            # Calculate stock dispatched amount for this sale order
            # Only for Sale Order lines where delivery has been completed (qty_delivered > 0)
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                if line.qty_delivered > 0:
                    # Dispatched amount = delivered quantity * unit price
                    dispatched_amount = line.qty_delivered * (line.price_unit or 0.0)
                    customer_data[partner_key]['stock_despatched_amount'] += dispatched_amount
            
            # Get payment information for this specific sale order
            # Method 1: Payments directly linked to this sale order via ks_sale_order_id
            payments_direct = self.env['account.payment'].search([
                ('ks_sale_order_id', '=', order.id),
                ('state', 'in', ['posted', 'paid'])
            ])
            
            # Method 2: Payments from invoices linked to this sale order
            invoices = self.env['account.move'].search([
                ('invoice_origin', '=', order_name),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted')
            ])
            
            # Collect all unique payments for this order
            all_payments = payments_direct
            
            # Get payments from invoices
            for invoice in invoices:
                try:
                    invoice_payments = invoice._get_reconciled_payments()
                    all_payments |= invoice_payments
                except:
                    pass
            
            # Method 3: Also check payments by partner that reference this sale order name
            payments_by_ref = self.env['account.payment'].search([
                ('partner_id', '=', partner.id),
                ('payment_type', '=', 'inbound'),  # Customer payments (money coming in)
                ('state', 'in', ['posted', 'paid'])
            ])
            
            # Filter payments that reference this sale order name
            for payment in payments_by_ref:
                # Safely get payment reference text from available fields
                payment_ref_parts = []
                if hasattr(payment, 'payment_reference') and payment.payment_reference:
                    payment_ref_parts.append(payment.payment_reference)
                if hasattr(payment, 'memo') and payment.memo:
                    payment_ref_parts.append(payment.memo)
                if hasattr(payment, 'name') and payment.name:
                    payment_ref_parts.append(payment.name)
                
                payment_ref = ' '.join(payment_ref_parts).upper()
                
                # Check if payment references this sale order name
                if payment_ref and order_name.upper() in payment_ref:
                    all_payments |= payment
            
            # Sum all payments for this sale order (avoid duplicates across all orders for this customer)
            for payment in all_payments:
                if payment.id not in customer_data[partner_key]['payment_ids_seen']:
                    customer_data[partner_key]['payment_ids_seen'].add(payment.id)
                    # Use amount field (this is the payment amount)
                    payment_amount = abs(payment.amount or 0.0)
                    customer_data[partner_key]['payment_received'] += payment_amount
        
        # Calculate balance for each customer
        for partner_key, data in customer_data.items():
            # Balance Available With Us = Payment Received - Stock Despatched Amount
            # Calculate dynamically: PAYMENT RECEIVED - STOCK DESPATCHED AMOUNT
            # If result is negative, show 0 (no negative values allowed)
            balance = data['payment_received'] - data['stock_despatched_amount']
            data['balance_available'] = max(0.0, balance)  # Ensure minimum is 0 (no negative values)
            # Remove the tracking set as we don't need it anymore
            del data['payment_ids_seen']
        
        # Write data rows - one row per customer with aggregated totals
        row = 1
        sr_no = 1
        total_payment_received = 0.0
        total_stock_despatched = 0.0
        total_balance = 0.0
        
        # Sort by party name
        sorted_customers = sorted(customer_data.items(), key=lambda x: x[1]['party_name'])
        
        for partner_key, data in sorted_customers:
            # SR NO.
            sheet.write(row, 0, sr_no, data_format)
            
            # PARTY NAME
            sheet.write(row, 1, data['party_name'], data_format)
            
            # PAYMENT RECEIVED (aggregated total for all sale orders of this customer)
            payment_received = data['payment_received'] or 0.0
            sheet.write(row, 2, payment_received, number_format)
            total_payment_received += payment_received
            
            # STOCK DESPATCHED AMOUNT (aggregated total for all sale orders of this customer)
            stock_despatched = data['stock_despatched_amount'] or 0.0
            sheet.write(row, 3, stock_despatched, number_format)
            total_stock_despatched += stock_despatched
            
            # BALANCE AVAILABLE WITH US (aggregated total for all sale orders of this customer)
            balance = data['balance_available'] or 0.0
            sheet.write(row, 4, balance, number_format)
            total_balance += balance
            
            row += 1
            sr_no += 1
        
        # Write total row
        total_row = row
        sheet.write(total_row, 0, '', total_format)
        sheet.write(total_row, 1, 'TOTAL', total_format)
        sheet.write(total_row, 2, total_payment_received, total_format)
        sheet.write(total_row, 3, total_stock_despatched, total_format)
        sheet.write(total_row, 4, total_balance, total_format)
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Return base64 encoded content
        return base64.b64encode(output.read())

    @api.model
    def generate_deepa_working_xlsx_report(self, partner_id=None):
        """
        Generate Deepa Working XLSX report with Sale Order, Payment, and Dispatch data
        Customer-wise report grouped by customer and Proforma Invoice
        If partner_id is provided, only show data for that customer
        Returns base64 encoded file content
        """
        from datetime import datetime
        from odoo import fields
        
        # Create output in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define header style with yellow background and bold text
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        
        # Define data row format
        data_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        
        # Define number format
        number_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0',
        })
        
        # Define number format with decimals
        number_format_decimal = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        
        # Define date format
        date_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': 'dd-mmm-yy',
        })
        
        # Define total row format (yellow background)
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0',
        })
        
        # Define column headings based on screenshots
        headers = [
            'PROFORMA INVOICE NO',
            'PROFORMA INVOICE DATE',
            'Currency',
            'Exchange Rate',
            'MODEL',
            'COLOR',
            'QTY',
            'TOTAL QTY',
            'RATE (INR)',
            'PI AMOUNT',
            'TOTAL AMOUNT',
            'PAYMENT RECEIVED (UTR Amounts)',
            'Bnak Charges, Currency Charges',
            'CN Amount',
            'Total Amount Received (TT Amount)',
            'Cross Check',
            'PAYMENT DATE',
            'BALANCE',
            'BANK NAME',
            'AD CODE',
            'DESPATCHED QTY',
            'PENDING QTY',
            'DESPATCHED DATE',
            'COMMERCIAL INVOICES',
            'DISPATCHED GOODS VALUE',
            'TOTAL STOCK VALUE DISPATCHED AGAINST PI',
            'STOCK VALUE TO BE DISPATCHED AGAINST PI',
        ]
        
        # Set column widths
        column_widths = [
            20,  # PROFORMA INVOICE NO
            18,  # PROFORMA INVOICE DATE
            12,  # Currency
            15,  # Exchange Rate
            40,  # MODEL
            15,  # COLOR
            12,  # QTY
            15,  # TOTAL QTY
            15,  # RATE (INR)
            18,  # PI AMOUNT
            18,  # TOTAL AMOUNT
            25,  # PAYMENT RECEIVED (UTR Amounts)
            25,  # Bnak Charges, Currency Charges
            15,  # CN Amount
            25,  # Total Amount Received (TT Amount)
            12,  # Cross Check
            15,  # PAYMENT DATE
            15,  # BALANCE
            20,  # BANK NAME
            15,  # AD CODE
            18,  # DESPATCHED QTY
            15,  # PENDING QTY
            18,  # DESPATCHED DATE
            20,  # COMMERCIAL INVOICES
            20,  # DISPATCHED GOODS VALUE
            35,  # TOTAL STOCK VALUE DISPATCHED AGAINST PI
            35,  # STOCK VALUE TO BE DISPATCHED AGAINST PI
        ]
        
        # Create worksheet
        sheet = workbook.add_worksheet('Deepa Working')
        
        # Write headers to first row
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        # Apply column widths
        for col, width in enumerate(column_widths):
            sheet.set_column(col, col, width)
        
        # Freeze first row
        sheet.freeze_panes(1, 0)
        
        # Get confirmed Sale Orders - filter by partner if provided
        domain = [('state', '=', 'sale')]
        if partner_id:
            # Include both the partner and its child contacts
            partner = self.env['res.partner'].browse(partner_id)
            partner_ids = partner.child_ids.ids + [partner_id]
            domain.append(('partner_id', 'in', partner_ids))
        
        sale_orders = self.env['sale.order'].search(domain, order='partner_id, name')
        
        row = 1
        group_start_row = 1
        
        for order in sale_orders:
            group_start_row = row
            
            # Get order-level data
            pi_no = order.name or ''
            pi_date = order.date_order or order.create_date
            currency = order.currency_id.name or ''
            
            # Get exchange rate (if multi-currency)
            exchange_rate = 1.0
            if order.currency_id and order.company_id.currency_id != order.currency_id:
                # Try to get rate from currency
                try:
                    rate = self.env['res.currency']._get_conversion_rate(
                        order.currency_id,
                        order.company_id.currency_id,
                        order.company_id,
                        order.date_order or fields.Date.today()
                    )
                    exchange_rate = rate if rate else 1.0
                except:
                    exchange_rate = 1.0
            
            # Get payment information
            # Try to get payments linked to sale order
            payments = self.env['account.payment'].search([
                ('ks_sale_order_id', '=', order.id),
                ('state', '=', 'posted')
            ])
            
            # Also try to get payments from invoices
            invoices = self.env['account.move'].search([
                ('invoice_origin', '=', order.name),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '=', 'posted')
            ])
            
            payment_received = 0.0
            payment_date = None
            bank_name = ''
            ad_code = ''
            
            for payment in payments:
                payment_received += payment.amount
                if not payment_date:
                    payment_date = payment.date
                if payment.journal_id and payment.journal_id.bank_account_id:
                    bank_name = payment.journal_id.bank_account_id.bank_id.name or ''
                    try:
                        ad_code = payment.journal_id.bank_account_id.ad_code or ''
                    except:
                        pass
            
            # Get payment from invoice payments
            for invoice in invoices:
                invoice_payments = invoice._get_reconciled_payments()
                for payment in invoice_payments:
                    payment_received += abs(payment.amount)
                    if not payment_date:
                        payment_date = payment.date
                    if payment.journal_id and payment.journal_id.bank_account_id:
                        if not bank_name:
                            bank_name = payment.journal_id.bank_account_id.bank_id.name or ''
                        if not ad_code:
                            try:
                                ad_code = payment.journal_id.bank_account_id.ad_code or ''
                            except:
                                pass
            
            # Calculate totals for this order
            total_qty = 0.0
            total_amount = 0.0
            total_pi_amount = 0.0
            total_dispatched_qty = 0.0
            total_dispatched_value = 0.0
            
            # Get pickings (deliveries)
            pickings = self.env['stock.picking'].search([
                ('sale_id', '=', order.id),
                ('state', '=', 'done')
            ], order='date_done')
            
            # Get commercial invoices
            commercial_invoices = []
            for invoice in invoices:
                if invoice.name:
                    commercial_invoices.append(invoice.name)
            
            # Process each order line
            order_lines = order.order_line.filtered(lambda l: not l.display_type and l.product_id)
            
            if not order_lines:
                continue
            
            for line in order_lines:
                # PROFORMA INVOICE NO
                sheet.write(row, 0, pi_no, data_format)
                
                # PROFORMA INVOICE DATE
                if pi_date:
                    sheet.write_datetime(row, 1, pi_date, date_format)
                
                # Currency
                sheet.write(row, 2, currency, data_format)
                
                # Exchange Rate
                sheet.write(row, 3, exchange_rate, number_format_decimal)
                
                # MODEL - Product name
                model_name = line.product_id.name if line.product_id else ''
                sheet.write(row, 4, model_name, data_format)
                
                # COLOR - Empty for now
                sheet.write(row, 5, '', data_format)
                
                # QTY - Ordered quantity
                qty = line.product_uom_qty or 0.0
                sheet.write(row, 6, qty, number_format)
                total_qty += qty
                
                # TOTAL QTY - Will be merged later
                sheet.write(row, 7, '', data_format)
                
                # RATE (INR) - Unit price (convert to INR if needed)
                rate_inr = line.price_unit
                if order.currency_id and order.company_id.currency_id.name == 'INR':
                    # Convert to INR if not already
                    if order.currency_id.name != 'INR':
                        rate_inr = line.price_unit * exchange_rate
                sheet.write(row, 8, rate_inr, number_format)
                
                # PI AMOUNT - Line amount
                pi_amount = line.price_subtotal or 0.0
                if order.currency_id and order.company_id.currency_id.name == 'INR':
                    if order.currency_id.name != 'INR':
                        pi_amount = line.price_subtotal * exchange_rate
                sheet.write(row, 9, pi_amount, number_format)
                total_pi_amount += pi_amount
                
                # TOTAL AMOUNT - Will be merged later
                sheet.write(row, 10, '', data_format)
                
                # PAYMENT RECEIVED (UTR Amounts) - Will be merged later
                sheet.write(row, 11, '', data_format)
                
                # Bnak Charges, Currency Charges - Empty
                sheet.write(row, 12, '', data_format)
                
                # CN Amount - Empty
                sheet.write(row, 13, '', data_format)
                
                # Total Amount Received (TT Amount) - Same as payment received
                sheet.write(row, 14, payment_received, number_format)
                
                # Cross Check - 0
                sheet.write(row, 15, 0, number_format)
                
                # PAYMENT DATE
                if payment_date:
                    sheet.write_datetime(row, 16, payment_date, date_format)
                else:
                    sheet.write(row, 16, '', data_format)
                
                # BALANCE - Will be calculated in last row
                sheet.write(row, 17, 0, number_format)
                
                # BANK NAME
                sheet.write(row, 18, bank_name, data_format)
                
                # AD CODE
                sheet.write(row, 19, ad_code, data_format)
                
                # DESPATCHED QTY - Delivered quantity
                dispatched_qty = line.qty_delivered or 0.0
                sheet.write(row, 20, dispatched_qty, number_format)
                total_dispatched_qty += dispatched_qty
                
                # PENDING QTY - Remaining quantity
                pending_qty = qty - dispatched_qty
                sheet.write(row, 21, pending_qty, number_format)
                
                # DESPATCHED DATE - From pickings
                dispatched_date = ''
                if pickings:
                    dispatched_date = pickings[0].date_done or ''
                if dispatched_date:
                    sheet.write_datetime(row, 22, dispatched_date, date_format)
                else:
                    sheet.write(row, 22, '', data_format)
                
                # COMMERCIAL INVOICES
                commercial_inv_str = ', '.join(commercial_invoices) if commercial_invoices else ''
                sheet.write(row, 23, commercial_inv_str, data_format)
                
                # DISPATCHED GOODS VALUE - Dispatched qty * rate
                dispatched_value = dispatched_qty * rate_inr
                sheet.write(row, 24, dispatched_value, number_format)
                total_dispatched_value += dispatched_value
                
                # TOTAL STOCK VALUE DISPATCHED AGAINST PI - Will be merged later
                sheet.write(row, 25, '', data_format)
                
                # STOCK VALUE TO BE DISPATCHED AGAINST PI - Remaining value
                stock_value_to_dispatch = pending_qty * rate_inr
                sheet.write(row, 26, stock_value_to_dispatch, number_format)
                
                row += 1
            
            # Write totals in merged cells for this group
            group_end_row = row - 1
            
            # Merge and write TOTAL QTY
            if group_start_row <= group_end_row:
                sheet.merge_range(group_start_row, 7, group_end_row, 7, total_qty, total_format)
                
                # Merge and write TOTAL AMOUNT
                total_amount = total_pi_amount
                sheet.merge_range(group_start_row, 10, group_end_row, 10, total_amount, total_format)
                
                # Merge and write PAYMENT RECEIVED
                sheet.merge_range(group_start_row, 11, group_end_row, 11, payment_received, total_format)
                
                # Merge and write TOTAL STOCK VALUE DISPATCHED AGAINST PI
                sheet.merge_range(group_start_row, 25, group_end_row, 25, total_dispatched_value, total_format)
                
                # Update BALANCE in last row of group
                balance = total_amount - payment_received
                sheet.write(group_end_row, 17, balance, number_format)
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Return base64 encoded content
        return base64.b64encode(output.read())

    @api.model
    def generate_advance_sheet_xlsx_report(self):
        """
        Advance Sheet: scan ALL sale orders, one row per customer (commercial partner).
        - PARTY NAME: customer name
        - PAYMENT RECEIVED: total paid (advance + invoice payments) across ALL their sale orders. NA if none.
        - STOCK DESPATCHED AMOUNT: total despatched value across ALL their sale orders. NA if none.
        - BALANCE AVAILABLE WITH US: Payment - Stock. NA if payment or delivery not done.
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
        })
        data_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'bg_color': '#ADD8E6',
        })
        number_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
            'bg_color': '#ADD8E6',
        })
        total_format = workbook.add_format({
            'bold': True,
            'border': 2,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        na_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'bg_color': '#ADD8E6',
        })
        
        headers = [
            'SR NO.',
            'PARTY NAME',
            'PAYMENT RECEIVED',
            'STOCK DESPATCHED AMOUNT',
            'BALANCE AVAILABLE WITH US',
        ]
        column_widths = [10, 30, 22, 28, 28]
        
        sheet = workbook.add_worksheet('Advance Sheet')
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        for col, width in enumerate(column_widths):
            sheet.set_column(col, col, width)
        sheet.freeze_panes(1, 0)
        
        # 1. Scan ALL sale orders (any state except cancel) to get every customer
        sale_orders = self.env['sale.order'].search([
            ('state', '!=', 'cancel')
        ], order='partner_id')
        
        # 2. Unique customers: by commercial partner (so same company = one row)
        commercial_partner_ids = set()
        for order in sale_orders:
            comp = order.partner_id.commercial_partner_id
            commercial_partner_ids.add(comp.id)
        
        # 3. For each customer, aggregate over ALL their sale orders
        company = self.env.company
        company_currency = company.currency_id
        party_data = {}
        for comp_id in commercial_partner_ids:
            comp = self.env['res.partner'].browse(comp_id)
            # All SOs where partner's commercial partner is this customer
            partner_orders = sale_orders.filtered(
                lambda o: o.partner_id.commercial_partner_id.id == comp_id
            )
            payment_received = 0.0
            stock_dispatched_amount = 0.0

            for order in partner_orders:
                # PAYMENT RECEIVED: advance payments from SO (same as on SO form: ks_advance_payment_ids)
                if hasattr(order, 'ks_advance_payment_ids') and order.ks_advance_payment_ids:
                    for pay in order.ks_advance_payment_ids.filtered(lambda p: p.state == 'posted'):
                        payment_received += _payment_to_company_currency(
                            pay, pay.amount, company_currency, company, self
                        )

                # PAYMENT RECEIVED: reconciled payments on invoices from this SO
                invoices = self.env['account.move'].search([
                    ('invoice_origin', '=', order.name),
                    ('move_type', 'in', ['out_invoice', 'out_refund']),
                    ('state', '=', 'posted'),
                ])
                for inv in invoices:
                    try:
                        for pay in inv._get_reconciled_payments():
                            payment_received += _payment_to_company_currency(
                                pay, abs(pay.amount), company_currency, company, self
                            )
                    except Exception:
                        pass

                # STOCK DESPATCHED AMOUNT: use qty_delivered * price_unit (reliable); optional move-based for sale_stock
                order_date = order.date_order.date() if order.date_order else fields.Date.context_today(self)
                order_currency = order.currency_id
                for line in order.order_line.filtered(
                    lambda l: not l.display_type and l.product_id
                ):
                    delivered_qty = 0.0
                    if getattr(line, 'qty_delivered_method', None) == 'stock_move' and getattr(line, '_get_outgoing_incoming_moves', None):
                        try:
                            outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
                            for move in outgoing_moves:
                                if move.state == 'done':
                                    delivered_qty += move.product_uom._compute_quantity(
                                        move.quantity, line.product_uom, rounding_method='HALF-UP'
                                    )
                            for move in incoming_moves:
                                if move.state == 'done':
                                    delivered_qty -= move.product_uom._compute_quantity(
                                        move.quantity, line.product_uom, rounding_method='HALF-UP'
                                    )
                        except Exception:
                            delivered_qty = line.qty_delivered
                    else:
                        delivered_qty = line.qty_delivered
                    if delivered_qty and (line.price_unit or 0.0):
                        line_amount = delivered_qty * (line.price_unit or 0.0)
                        stock_dispatched_amount += _to_company_currency(
                            order_currency, line_amount, company_currency, company, order_date, self
                        )
            
            party_data[comp_id] = {
                'party_name': comp.name or '',
                'payment_received': payment_received,
                'stock_dispatched_amount': stock_dispatched_amount,
            }
        
        # BALANCE AVAILABLE WITH US: Payment - Stock; NA when payment or delivery not done
        for data in party_data.values():
            pr = data['payment_received']
            sd = data['stock_dispatched_amount']
            if pr == 0 or sd == 0:
                data['balance_available'] = None
            else:
                data['balance_available'] = pr - sd
        
        # 4. Write all rows
        row = 1
        sr_no = 1
        total_payment_received = 0.0
        total_stock_dispatched = 0.0
        total_balance = 0.0
        total_balance_count = 0
        
        sorted_parties = sorted(
            party_data.items(),
            key=lambda x: (x[1]['party_name'] or '').lower()
        )
        
        for _partner_key, data in sorted_parties:
            sheet.write(row, 0, sr_no, data_format)
            sheet.write(row, 1, data['party_name'], data_format)
            
            pr = data['payment_received'] or 0.0
            if pr == 0:
                sheet.write(row, 2, 'NA', na_format)
            else:
                sheet.write(row, 2, pr, number_format)
                total_payment_received += pr
            
            sd = data['stock_dispatched_amount'] or 0.0
            if sd == 0:
                sheet.write(row, 3, 'NA', na_format)
            else:
                sheet.write(row, 3, sd, number_format)
                total_stock_dispatched += sd
            
            bal = data.get('balance_available')
            if bal is None:
                sheet.write(row, 4, 'NA', na_format)
            else:
                sheet.write(row, 4, bal, number_format)
                total_balance += bal
                total_balance_count += 1
            
            row += 1
            sr_no += 1
        
        total_row = row
        sheet.write(total_row, 0, '', total_format)
        sheet.write(total_row, 1, 'TOTAL', total_format)
        sheet.write(total_row, 2, total_payment_received if total_payment_received else 'NA', total_format)
        sheet.write(total_row, 3, total_stock_dispatched if total_stock_dispatched else 'NA', total_format)
        sheet.write(total_row, 4, total_balance if total_balance_count else 'NA', total_format)
        
        workbook.close()
        output.seek(0)
        return base64.b64encode(output.read())

    @api.model
    def generate_exchange_gl_xlsx_report(self):
        """
        Generate Exchange GL XLSX report with Proforma Invoice, Commercial Invoice, 
        Shipping Bill, and Payment data with exchange rate calculations
        Based on screenshot structure with grouped data by Proforma Invoice
        Returns base64 encoded file content
        """
        from datetime import datetime
        from odoo import fields
        
        # Create output in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define header style with yellow background and bold text
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        
        # Define data row format
        data_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        
        # Define number format
        number_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0',
        })
        
        # Define number format with decimals
        number_format_decimal = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        
        # Define date format
        date_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': 'dd-mmm-yy',
        })
        
        # Define column headings based on screenshot
        headers = [
            'PROFORMA INVOICE NO',
            'PROFORMA INVOICE DATE',
            'Currency',
            'Exchange Rate on PI Date',
            'QTY',
            'TOTAL QTY',
            'RATE (INR)',
            'PI AMOUNT',
            'TOTAL AMOUNT',
            'COMMERCIAL INVOICES',
            'COMMERCIAL INVOICES Date',
            'COMMERCIAL INVOICES Amount',
            'Shipping Bill (SB) No',
            'Shipping Bill Date',
            'Shipping Bill Value USD/AED/HKD',
            'Exchange Rate SB',
            'Shipping Bill Value INR',
            'Total Amount Received (TT Amount) USD/AED/HKD',
            'Bank Charges, Currency Charges USD/AED/HKD',
            'Net Amount Received USD/AED/HKD',
            'Exchange Rate on Remittance Date',
            'PAYMENT RECEIVED INR',
            'Exchange Gain or Loss',
        ]
        
        # Set column widths
        column_widths = [
            20,  # PROFORMA INVOICE NO
            18,  # PROFORMA INVOICE DATE
            12,  # Currency
            20,  # Exchange Rate on PI Date
            10,  # QTY
            12,  # TOTAL QTY
            15,  # RATE (INR)
            15,  # PI AMOUNT
            15,  # TOTAL AMOUNT
            20,  # COMMERCIAL INVOICES
            20,  # COMMERCIAL INVOICES Date
            20,  # COMMERCIAL INVOICES Amount
            20,  # Shipping Bill (SB) No
            18,  # Shipping Bill Date
            25,  # Shipping Bill Value USD/AED/HKD
            18,  # Exchange Rate SB
            20,  # Shipping Bill Value INR
            30,  # Total Amount Received (TT Amount) USD/AED/HKD
            30,  # Bank Charges, Currency Charges USD/AED/HKD
            25,  # Net Amount Received USD/AED/HKD
            28,  # Exchange Rate on Remittance Date
            20,  # PAYMENT RECEIVED INR
            20,  # Exchange Gain or Loss
        ]
        
        # Create worksheet
        sheet = workbook.add_worksheet('Exchange GL')
        
        # Write headers to first row
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        # Apply column widths
        for col, width in enumerate(column_widths):
            sheet.set_column(col, col, width)
        
        # Freeze first row
        sheet.freeze_panes(1, 0)
        
        # Get all confirmed Sale Orders
        sale_orders = self.env['sale.order'].search([
            ('state', 'in', ['sale', 'done'])
        ], order='name, date_order')
        
        # Group orders by Proforma Invoice (Sale Order)
        row = 1
        
        for order in sale_orders:
            # Get order lines (excluding section/note lines)
            order_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id
            )
            
            if not order_lines:
                continue
            
            # Proforma Invoice details
            pi_no = order.name or ''
            pi_date = order.date_order or order.create_date
            
            # Format date
            if pi_date:
                if isinstance(pi_date, str):
                    try:
                        pi_date = fields.Datetime.from_string(pi_date)
                    except:
                        pi_date = None
                if pi_date:
                    pi_date_str = pi_date.strftime('%d-%b-%y') if hasattr(pi_date, 'strftime') else str(pi_date)
                else:
                    pi_date_str = ''
            else:
                pi_date_str = ''
            
            # Get currency
            currency = order.currency_id
            currency_code = currency.name if currency else ''
            
            # Calculate exchange rate on PI date (simplified - using currency rate)
            # In real scenario, this would come from currency rate table
            exchange_rate_pi = 1.0
            if currency and currency.name != 'INR':
                # Try to get rate from currency
                rate_obj = self.env['res.currency.rate'].search([
                    ('currency_id', '=', currency.id),
                    ('name', '<=', pi_date.date() if hasattr(pi_date, 'date') else fields.Date.today())
                ], order='name desc', limit=1)
                if rate_obj:
                    exchange_rate_pi = rate_obj.rate or 1.0
                else:
                    # Fallback: use current rate
                    exchange_rate_pi = currency.rate if hasattr(currency, 'rate') else 1.0
            
            # Calculate total quantity and total amount for the order
            total_qty = sum(order_lines.mapped('product_uom_qty'))
            total_amount = order.amount_total
            
            # Get commercial invoices
            commercial_invoices = self.env['account.move'].search([
                ('invoice_origin', '=', order.name),
                ('move_type', 'in', ['out_invoice', 'out_refund']),
                ('state', '!=', 'cancel')
            ], order='invoice_date desc')
            
            commercial_inv_names = []
            commercial_inv_dates = []
            commercial_inv_amounts = []
            
            for inv in commercial_invoices:
                commercial_inv_names.append(inv.name or '')
                if inv.invoice_date:
                    commercial_inv_dates.append(inv.invoice_date.strftime('%d-%b-%y') if hasattr(inv.invoice_date, 'strftime') else str(inv.invoice_date))
                else:
                    commercial_inv_dates.append('')
                commercial_inv_amounts.append(inv.amount_total or 0.0)
            
            commercial_inv_str = ', '.join(commercial_inv_names) if commercial_inv_names else ''
            commercial_inv_date_str = ', '.join(commercial_inv_dates) if commercial_inv_dates else ''
            commercial_inv_total = sum(commercial_inv_amounts) if commercial_inv_amounts else 0.0
            
            # Get shipping bills (from stock pickings)
            pickings = self.env['stock.picking'].search([
                ('sale_id', '=', order.id),
                ('state', '=', 'done')
            ], order='date_done desc')
            
            sb_numbers = []
            sb_dates = []
            sb_values = []
            sb_exchange_rates = []
            
            for picking in pickings:
                # Try to get shipping bill number from picking name or custom field
                sb_no = picking.name or ''
                if hasattr(picking, 'l10n_in_shipping_bill_no') and picking.l10n_in_shipping_bill_no:
                    sb_no = picking.l10n_in_shipping_bill_no
                
                if sb_no:
                    sb_numbers.append(sb_no)
                    if picking.date_done:
                        sb_dates.append(picking.date_done.strftime('%d-%b-%y') if hasattr(picking.date_done, 'strftime') else str(picking.date_done))
                    else:
                        sb_dates.append('')
                    
                    # Calculate shipping bill value (from delivered quantities)
                    sb_value = 0.0
                    for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
                        if move.sale_line_id:
                            # Use quantity from move (for done moves, this is the quantity done)
                            # Or sum quantity from move lines
                            qty_done = move.quantity
                            if not qty_done and move.move_line_ids:
                                qty_done = sum(move.move_line_ids.mapped('quantity'))
                            sb_value += qty_done * (move.sale_line_id.price_unit or 0.0)
                    sb_values.append(sb_value)
                    
                    # Get exchange rate for shipping bill date
                    sb_exchange_rate = exchange_rate_pi  # Default to PI rate
                    if picking.date_done and currency and currency.name != 'INR':
                        rate_obj = self.env['res.currency.rate'].search([
                            ('currency_id', '=', currency.id),
                            ('name', '<=', picking.date_done.date() if hasattr(picking.date_done, 'date') else fields.Date.today())
                        ], order='name desc', limit=1)
                        if rate_obj:
                            sb_exchange_rate = rate_obj.rate or exchange_rate_pi
                    sb_exchange_rates.append(sb_exchange_rate)
            
            sb_no_str = ', '.join(sb_numbers) if sb_numbers else ''
            sb_date_str = ', '.join(sb_dates) if sb_dates else ''
            sb_value_total = sum(sb_values) if sb_values else 0.0
            sb_value_inr = sb_value_total * (sb_exchange_rates[0] if sb_exchange_rates else exchange_rate_pi) if sb_value_total > 0 else 0.0
            
            # Get payment information
            payments = self.env['account.payment'].search([
                ('ks_sale_order_id', '=', order.id),
                ('state', '=', 'posted')
            ])
            
            # Also get payments from invoices
            for invoice in commercial_invoices:
                invoice_payments = invoice._get_reconciled_payments()
                payments |= invoice_payments
            
            total_amount_received = 0.0
            bank_charges = 0.0
            net_amount_received = 0.0
            payment_exchange_rate = exchange_rate_pi
            payment_received_inr = 0.0
            
            payment_dates = []
            for payment in payments:
                total_amount_received += abs(payment.amount)
                if payment.date:
                    payment_dates.append(payment.date)
                    # Get exchange rate on payment date
                    if currency and currency.name != 'INR':
                        rate_obj = self.env['res.currency.rate'].search([
                            ('currency_id', '=', currency.id),
                            ('name', '<=', payment.date)
                        ], order='name desc', limit=1)
                        if rate_obj:
                            payment_exchange_rate = rate_obj.rate or exchange_rate_pi
            
            net_amount_received = total_amount_received - bank_charges
            payment_received_inr = net_amount_received * payment_exchange_rate if net_amount_received > 0 else 0.0
            
            # Calculate exchange gain or loss
            # Gain/Loss = (Payment Received INR) - (PI Amount in INR)
            pi_amount_inr = total_amount * exchange_rate_pi if currency and currency.name != 'INR' else total_amount
            exchange_gain_loss = payment_received_inr - pi_amount_inr if payment_received_inr > 0 else 0.0
            
            # Write data for each order line
            group_start_row = row
            for line in order_lines:
                # PROFORMA INVOICE NO
                sheet.write(row, 0, pi_no, data_format)
                
                # PROFORMA INVOICE DATE
                sheet.write(row, 1, pi_date_str, date_format)
                
                # Currency
                sheet.write(row, 2, currency_code, data_format)
                
                # Exchange Rate on PI Date
                sheet.write(row, 3, exchange_rate_pi, number_format_decimal)
                
                # QTY
                qty = line.product_uom_qty or 0.0
                sheet.write(row, 4, qty, number_format)
                
                # TOTAL QTY (will be merged later)
                sheet.write(row, 5, '', data_format)
                
                # RATE (INR)
                rate_inr = line.price_unit * exchange_rate_pi if currency and currency.name != 'INR' else line.price_unit
                if row == group_start_row:  # Only show rate in first row
                    sheet.write(row, 6, rate_inr, number_format)
                else:
                    sheet.write(row, 6, '', data_format)
                
                # PI AMOUNT
                sheet.write(row, 7, '', data_format)
                
                # TOTAL AMOUNT (will be merged later)
                sheet.write(row, 8, '', data_format)
                
                # COMMERCIAL INVOICES
                if row == group_start_row:
                    sheet.write(row, 9, commercial_inv_str, data_format)
                else:
                    sheet.write(row, 9, '', data_format)
                
                # COMMERCIAL INVOICES Date
                if row == group_start_row:
                    sheet.write(row, 10, commercial_inv_date_str, data_format)
                else:
                    sheet.write(row, 10, '', data_format)
                
                # COMMERCIAL INVOICES Amount
                if row == group_start_row:
                    sheet.write(row, 11, commercial_inv_total, number_format)
                else:
                    sheet.write(row, 11, '', data_format)
                
                # Shipping Bill (SB) No
                if row == group_start_row:
                    sheet.write(row, 12, sb_no_str, data_format)
                else:
                    sheet.write(row, 12, '', data_format)
                
                # Shipping Bill Date
                if row == group_start_row:
                    sheet.write(row, 13, sb_date_str, date_format)
                else:
                    sheet.write(row, 13, '', data_format)
                
                # Shipping Bill Value USD/AED/HKD
                if row == group_start_row:
                    sheet.write(row, 14, sb_value_total if sb_value_total > 0 else '', number_format)
                else:
                    sheet.write(row, 14, '', data_format)
                
                # Exchange Rate SB
                if row == group_start_row:
                    sheet.write(row, 15, sb_exchange_rates[0] if sb_exchange_rates else '', number_format_decimal)
                else:
                    sheet.write(row, 15, '', data_format)
                
                # Shipping Bill Value INR
                if row == group_start_row:
                    sheet.write(row, 16, sb_value_inr if sb_value_inr > 0 else '', number_format)
                else:
                    sheet.write(row, 16, '', data_format)
                
                # Total Amount Received (TT Amount) USD/AED/HKD
                if row == group_start_row:
                    sheet.write(row, 17, total_amount_received if total_amount_received > 0 else '', number_format)
                else:
                    sheet.write(row, 17, '', data_format)
                
                # Bank Charges, Currency Charges USD/AED/HKD
                if row == group_start_row:
                    sheet.write(row, 18, bank_charges if bank_charges > 0 else '', number_format)
                else:
                    sheet.write(row, 18, '', data_format)
                
                # Net Amount Received USD/AED/HKD
                if row == group_start_row:
                    sheet.write(row, 19, net_amount_received if net_amount_received > 0 else '', number_format)
                else:
                    sheet.write(row, 19, '', data_format)
                
                # Exchange Rate on Remittance Date
                if row == group_start_row:
                    sheet.write(row, 20, payment_exchange_rate if payment_exchange_rate != exchange_rate_pi else '', number_format_decimal)
                else:
                    sheet.write(row, 20, '', data_format)
                
                # PAYMENT RECEIVED INR
                if row == group_start_row:
                    sheet.write(row, 21, payment_received_inr if payment_received_inr > 0 else '', number_format)
                else:
                    sheet.write(row, 21, '', data_format)
                
                # Exchange Gain or Loss
                if row == group_start_row:
                    sheet.write(row, 22, exchange_gain_loss if exchange_gain_loss != 0 else '', number_format)
                else:
                    sheet.write(row, 22, '', data_format)
                
                row += 1
            
            # Merge cells for grouped columns
            group_end_row = row - 1
            if group_end_row > group_start_row:
                # Merge TOTAL QTY
                sheet.merge_range(group_start_row, 5, group_end_row, 5, total_qty, number_format)
                
                # Merge TOTAL AMOUNT
                sheet.merge_range(group_start_row, 8, group_end_row, 8, total_amount, number_format)
                
                # Merge COMMERCIAL INVOICES columns
                sheet.merge_range(group_start_row, 9, group_end_row, 9, commercial_inv_str, data_format)
                sheet.merge_range(group_start_row, 10, group_end_row, 10, commercial_inv_date_str, data_format)
                sheet.merge_range(group_start_row, 11, group_end_row, 11, commercial_inv_total, number_format)
                
                # Merge Shipping Bill columns
                sheet.merge_range(group_start_row, 12, group_end_row, 12, sb_no_str, data_format)
                sheet.merge_range(group_start_row, 13, group_end_row, 13, sb_date_str, date_format)
                sheet.merge_range(group_start_row, 14, group_end_row, 14, sb_value_total if sb_value_total > 0 else '', number_format)
                sheet.merge_range(group_start_row, 15, group_end_row, 15, sb_exchange_rates[0] if sb_exchange_rates else '', number_format_decimal)
                sheet.merge_range(group_start_row, 16, group_end_row, 16, sb_value_inr if sb_value_inr > 0 else '', number_format)
                
                # Merge Payment columns
                sheet.merge_range(group_start_row, 17, group_end_row, 17, total_amount_received if total_amount_received > 0 else '', number_format)
                sheet.merge_range(group_start_row, 18, group_end_row, 18, bank_charges if bank_charges > 0 else '', number_format)
                sheet.merge_range(group_start_row, 19, group_end_row, 19, net_amount_received if net_amount_received > 0 else '', number_format)
                sheet.merge_range(group_start_row, 20, group_end_row, 20, payment_exchange_rate if payment_exchange_rate != exchange_rate_pi else '', number_format_decimal)
                sheet.merge_range(group_start_row, 21, group_end_row, 21, payment_received_inr if payment_received_inr > 0 else '', number_format)
                sheet.merge_range(group_start_row, 22, group_end_row, 22, exchange_gain_loss if exchange_gain_loss != 0 else '', number_format)
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Return base64 encoded content
        return base64.b64encode(output.read())

    @api.model
    def generate_sheet_2_xlsx_report(self, sale_order_ids=None):
        """
        Generate Sheet 2 XLSX report - Sales Order-wise report
        Each row represents one Sale Order line (product) with dynamic Export Invoice columns
        If sale_order_ids provided, only those orders are included
        Returns base64 encoded file content
        """
        # Create output in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define header style with yellow background and bold text
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        
        # Define data row format
        data_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        
        # Define number format
        number_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        
        # Define total row format with yellow background
        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'valign': 'vcenter',
        })
        
        # Define total row number format with yellow background
        total_number_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        
        # Get Sale Orders - if IDs provided, use those; otherwise get all confirmed
        if sale_order_ids:
            sale_orders = self.env['sale.order'].browse(sale_order_ids).filtered(
                lambda so: so.state in ['sale', 'done']
            )
        else:
            sale_orders = self.env['sale.order'].search([
                ('state', 'in', ['sale', 'done'])
            ], order='name')
        
        if not sale_orders:
            # Return empty workbook if no orders
            workbook.close()
            output.seek(0)
            return base64.b64encode(output.read())
        
        # Collect all invoices linked to these sale orders
        all_invoices = self.env['account.move'].search([
            ('invoice_origin', 'in', sale_orders.mapped('name')),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', '!=', 'cancel')
        ], order='name')
        
        # Extract unique invoice numbers and create dynamic column mapping
        invoice_columns = {}
        invoice_col_index = 0
        base_col_count = 5  # SR NO, Particulars, Total Quantity, Rate Per Piece, PI Amount
        
        for invoice in all_invoices:
            invoice_name = invoice.name or ''
            if invoice_name:
                # Extract last numeric part from invoice number
                # Example: INV/2026/00008 -> 00008
                digits = re.findall(r'\d+', invoice_name)
                if digits:
                    # Get last sequence of digits (usually the invoice number part)
                    last_digits = digits[-1]
                    # Ensure it's 5 digits (pad with zeros if needed)
                    invoice_suffix = last_digits[-5:].zfill(5)
                    column_name = f'EXPORT INVOICE-{invoice_suffix}'
                    
                    # Only add if not already added (avoid duplicates)
                    if column_name not in invoice_columns:
                        invoice_columns[column_name] = {
                            'invoice_id': invoice.id,
                            'invoice_name': invoice_name,
                            'col_index': base_col_count + invoice_col_index
                        }
                        invoice_col_index += 1
        
        # Define base column headings
        headers = [
            'SR NO.',
            'PARTICULARS',
            'TOTAL QUANTITY',
            'RATE PER PIECE',
            'PI AMOUNT',
        ]
        
        # Add dynamic Export Invoice columns (sorted by column index)
        sorted_invoice_cols = sorted(invoice_columns.items(), key=lambda x: x[1]['col_index'])
        for col_name, col_info in sorted_invoice_cols:
            headers.append(col_name)
        
        # Add remaining fixed columns
        headers.extend([
            'DISPATCH QUANTITY',
            'REMAINING QUANTITY',
            'DISPATCH AMOUNT',
            'TOTAL REMAINING AMOUNT',
            'EXP INV - 38 and CI6',
        ])
        
        # Set column widths
        column_widths = [
            10,  # SR NO.
            40,  # PARTICULARS
            15,  # TOTAL QUANTITY
            15,  # RATE PER PIECE
            18,  # PI AMOUNT
        ]
        
        # Add widths for dynamic invoice columns
        for _ in invoice_columns:
            column_widths.append(20)  # Export Invoice columns
        
        # Add widths for remaining columns
        column_widths.extend([
            18,  # DISPATCH QUANTITY
            18,  # REMAINING QUANTITY
            18,  # DISPATCH AMOUNT
            25,  # TOTAL REMAINING AMOUNT
            20,  # EXP INV - 38 and CI6
        ])
        
        # Create main report sheet (this is the printable report)
        # Sheet2 remains as a conceptual backend data source (data is processed in memory)
        report_sheet = workbook.add_worksheet('Report')
        
        # Write headers to first row
        for col, header in enumerate(headers):
            report_sheet.write(0, col, header, header_format)
        
        # Apply column widths
        for col, width in enumerate(column_widths):
            report_sheet.set_column(col, col, width)
        
        # Freeze first row
        report_sheet.freeze_panes(1, 0)
        
        # Process Sale Orders - one row per order line (product)
        row = 1
        sr_no = 1
        
        # Initialize totals
        total_quantity_sum = 0.0
        pi_amount_sum = 0.0
        dispatch_quantity_sum = 0.0
        remaining_quantity_sum = 0.0
        dispatch_amount_sum = 0.0
        total_remaining_amount_sum = 0.0
        invoice_totals = {}  # Dictionary to store totals for each invoice column
        
        for order in sale_orders:
            # Get invoices for this sale order
            order_invoices = all_invoices.filtered(lambda inv: inv.invoice_origin == order.name)
            
            # Process each order line (product) as a separate row
            for line in order.order_line.filtered(lambda l: not l.display_type and l.product_id):
                col = 0
                
                # SR NO.
                report_sheet.write(row, col, sr_no, data_format)
                col += 1
                
                # PARTICULARS (Product name)
                product_name = line.product_id.name if line.product_id else ''
                report_sheet.write(row, col, product_name, data_format)
                col += 1
                
                # TOTAL QUANTITY
                total_quantity = line.product_uom_qty or 0.0
                report_sheet.write(row, col, total_quantity, number_format)
                total_quantity_sum += total_quantity
                col += 1
                
                # RATE PER PIECE
                rate_per_piece = line.price_unit or 0.0
                report_sheet.write(row, col, rate_per_piece, number_format)
                col += 1
                
                # PI AMOUNT
                pi_amount = line.price_subtotal or 0.0
                report_sheet.write(row, col, pi_amount, number_format)
                pi_amount_sum += pi_amount
                col += 1
                
                # Dynamic Export Invoice columns - show quantities per invoice
                for col_name, col_info in sorted_invoice_cols:
                    invoice_id = col_info['invoice_id']
                    invoice_name = col_info['invoice_name']
                    
                    # Find invoice lines for this product in this invoice
                    invoice = self.env['account.move'].browse(invoice_id)
                    invoice_lines = invoice.invoice_line_ids.filtered(
                        lambda il: il.product_id.id == line.product_id.id and (
                            line.id in il.sale_line_ids.ids if il.sale_line_ids else True
                        ) and invoice.invoice_origin == order.name
                    )
                    
                    # Calculate total quantity for this product in this invoice
                    invoice_quantity = sum(invoice_lines.mapped('quantity')) if invoice_lines else 0.0
                    abs_invoice_quantity = abs(invoice_quantity)
                    report_sheet.write(row, col, abs_invoice_quantity, number_format)
                    
                    # Add to invoice totals
                    if col_name not in invoice_totals:
                        invoice_totals[col_name] = 0.0
                    invoice_totals[col_name] += abs_invoice_quantity
                    
                    col += 1
                
                # DISPATCH QUANTITY
                dispatch_quantity = line.qty_delivered or 0.0
                report_sheet.write(row, col, dispatch_quantity, number_format)
                dispatch_quantity_sum += dispatch_quantity
                col += 1
                
                # REMAINING QUANTITY
                remaining_quantity = total_quantity - dispatch_quantity
                report_sheet.write(row, col, remaining_quantity, number_format)
                remaining_quantity_sum += remaining_quantity
                col += 1
                
                # DISPATCH AMOUNT
                dispatch_amount = dispatch_quantity * rate_per_piece
                report_sheet.write(row, col, dispatch_amount, number_format)
                dispatch_amount_sum += dispatch_amount
                col += 1
                
                # TOTAL REMAINING AMOUNT
                total_remaining_amount = remaining_quantity * rate_per_piece
                report_sheet.write(row, col, total_remaining_amount, number_format)
                total_remaining_amount_sum += total_remaining_amount
                col += 1
                
                # EXP INV - 38 and CI6 (empty, reserved for future use)
                report_sheet.write(row, col, '', data_format)
                
                row += 1
                sr_no += 1
        
        # Add TOTAL row
        if row > 1:  # Only add total row if there are data rows
            total_row = row
            col = 0
            
            # SR NO. - empty
            report_sheet.write(total_row, col, '', total_format)
            col += 1
            
            # PARTICULARS - "TOTAL"
            report_sheet.write(total_row, col, 'TOTAL', total_format)
            col += 1
            
            # TOTAL QUANTITY - sum
            report_sheet.write(total_row, col, total_quantity_sum, total_number_format)
            col += 1
            
            # RATE PER PIECE - empty
            report_sheet.write(total_row, col, '', total_format)
            col += 1
            
            # PI AMOUNT - sum
            report_sheet.write(total_row, col, pi_amount_sum, total_number_format)
            col += 1
            
            # Dynamic Export Invoice columns - show totals
            for col_name, col_info in sorted_invoice_cols:
                invoice_total = invoice_totals.get(col_name, 0.0)
                report_sheet.write(total_row, col, invoice_total, total_number_format)
                col += 1
            
            # DISPATCH QUANTITY - sum
            report_sheet.write(total_row, col, dispatch_quantity_sum, total_number_format)
            col += 1
            
            # REMAINING QUANTITY - sum
            report_sheet.write(total_row, col, remaining_quantity_sum, total_number_format)
            col += 1
            
            # DISPATCH AMOUNT - sum
            report_sheet.write(total_row, col, dispatch_amount_sum, total_number_format)
            col += 1
            
            # TOTAL REMAINING AMOUNT - sum
            report_sheet.write(total_row, col, total_remaining_amount_sum, total_number_format)
            col += 1
            
            # EXP INV - 38 and CI6 - empty
            report_sheet.write(total_row, col, '', total_format)
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Return base64 encoded content
        return base64.b64encode(output.read())

    @api.model
    def generate_cn_tracking_xlsx_report(self, sale_order_ids=None, credit_note_ids=None):
        """
        Generate CN Tracking XLSX report - Proforma Invoice, Commercial Invoice, and Credit Note tracking.
        - If credit_note_ids is provided: report shows only rows for those Credit Notes (used when printing from Credit Notes).
        - Otherwise: shows Sale Order level tracking with PI, Commercial Invoice, and CN details.
        Returns base64 encoded file content.
        """
        # Create output in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define header style with yellow background and bold text
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        
        # Define data row format
        data_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        
        # Define number format
        number_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        
        # Define date format
        date_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': 'dd-mmm-yy',
        })
        
        # Define column headings
        headers = [
            'PROFORMA INVOICE NO',
            'PROFORMA INVOICE DATE',
            'PI AMOUNT',
            'COMMERCIAL INVOICE NO',
            'COMMERCIAL INVOICE DATE',
            'COMMERCIAL INVOICE AMOUNT',
            'CN DATE',
            'CN NO',
            'CN AMOUNT',
            'CN Adjusted Against PI No.',
            'Adjustment Amount',
            'Balance CN',
        ]
        
        column_widths = [
            25, 20, 18, 25, 20, 25, 18, 20, 18, 25, 20, 18,
        ]
        
        # Create worksheet
        sheet = workbook.add_worksheet('CN Tracking')
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        for col, width in enumerate(column_widths):
            sheet.set_column(col, col, width)
        sheet.freeze_panes(1, 0)
        
        row = 1
        
        # When data is "Credit Notes only": only include these credit note rows (no sale order dump)
        if credit_note_ids is not None:
            credit_notes = self.env['account.move'].browse(credit_note_ids).filtered(
                lambda m: m.move_type == 'out_refund' and m.state != 'cancel'
            )
            for cn in credit_notes.sorted(key=lambda m: (m.invoice_date or m.create_date, m.name or '')):
                order = None
                if cn.invoice_origin:
                    order = self.env['sale.order'].search([('name', '=', cn.invoice_origin)], limit=1)
                if not order and cn.reversed_entry_id and cn.reversed_entry_id.invoice_origin:
                    order = self.env['sale.order'].search([('name', '=', cn.reversed_entry_id.invoice_origin)], limit=1)
                pi_no = order.name if order else (cn.invoice_origin or '')
                pi_date = order.date_order or order.create_date if order else None
                pi_amount = order.amount_total if order else 0.0
                related_invoice = cn.reversed_entry_id
                if not related_invoice and cn.invoice_origin:
                    related_invoice = self.env['account.move'].search([
                        ('invoice_origin', '=', cn.invoice_origin),
                        ('move_type', '=', 'out_invoice'),
                        ('state', '!=', 'cancel')
                    ], limit=1)
                commercial_invoice_no = related_invoice.name if related_invoice else ''
                cn_amount = abs(cn.amount_total_signed) if cn.amount_total_signed else abs(cn.amount_total) if cn.amount_total else 0.0
                adjusted_pi_no = cn.invoice_origin or (related_invoice.invoice_origin if related_invoice else '') or pi_no
                adjustment_amount = 0.0
                if cn.amount_residual == 0:
                    adjustment_amount = cn_amount
                else:
                    adjustment_amount = cn_amount - abs(cn.amount_residual)
                balance_cn = cn_amount - adjustment_amount
                col = 0
                sheet.write(row, col, pi_no, data_format)
                col += 1
                if pi_date:
                    sheet.write(row, col, pi_date, date_format)
                else:
                    sheet.write(row, col, '', data_format)
                col += 1
                sheet.write(row, col, pi_amount, number_format)
                col += 1
                sheet.write(row, col, commercial_invoice_no, data_format)
                col += 1
                if related_invoice and related_invoice.invoice_date:
                    sheet.write(row, col, related_invoice.invoice_date, date_format)
                else:
                    sheet.write(row, col, '', data_format)
                col += 1
                if related_invoice:
                    sheet.write(row, col, related_invoice.amount_total or 0.0, number_format)
                else:
                    sheet.write(row, col, '', data_format)
                col += 1
                if cn.invoice_date:
                    sheet.write(row, col, cn.invoice_date, date_format)
                else:
                    sheet.write(row, col, '', data_format)
                col += 1
                sheet.write(row, col, cn.name or '', data_format)
                col += 1
                sheet.write(row, col, cn_amount, number_format)
                col += 1
                sheet.write(row, col, adjusted_pi_no, data_format)
                col += 1
                sheet.write(row, col, adjustment_amount, number_format)
                col += 1
                sheet.write(row, col, balance_cn, number_format)
                row += 1
            workbook.close()
            output.seek(0)
            return base64.b64encode(output.read())
        
        # Get Sale Orders - if IDs provided, use those; otherwise get all confirmed
        if sale_order_ids:
            sale_orders = self.env['sale.order'].browse(sale_order_ids).filtered(
                lambda so: so.state in ['sale', 'done']
            )
        else:
            sale_orders = self.env['sale.order'].search([
                ('state', 'in', ['sale', 'done'])
            ], order='name')
        
        if not sale_orders:
            workbook.close()
            output.seek(0)
            return base64.b64encode(output.read())
        
        # Process Sale Orders
        for order in sale_orders:
            # Proforma Invoice details (from Sale Order)
            pi_no = order.name or ''
            pi_date = order.date_order or order.create_date
            pi_amount = order.amount_total or 0.0
            
            # Get Commercial Invoices for this Sale Order
            commercial_invoices = self.env['account.move'].search([
                ('invoice_origin', '=', order.name),
                ('move_type', 'in', ['out_invoice']),
                ('state', '!=', 'cancel')
            ], order='name')
            
            # Get Credit Notes related to this Sale Order or its Commercial Invoices
            credit_notes = self.env['account.move'].search([
                '|',
                ('invoice_origin', '=', order.name),
                ('reversed_entry_id', 'in', commercial_invoices.ids),
                ('move_type', '=', 'out_refund'),
                ('state', '!=', 'cancel')
            ], order='name')
            
            # If there are Commercial Invoices or Credit Notes, create rows for each
            if commercial_invoices or credit_notes:
                # Create a row for each Commercial Invoice
                for invoice in commercial_invoices:
                    col = 0
                    
                    # PROFORMA INVOICE NO
                    sheet.write(row, col, pi_no, data_format)
                    col += 1
                    
                    # PROFORMA INVOICE DATE
                    if pi_date:
                        sheet.write(row, col, pi_date, date_format)
                    col += 1
                    
                    # PI AMOUNT
                    sheet.write(row, col, pi_amount, number_format)
                    col += 1
                    
                    # COMMERCIAL INVOICE NO
                    sheet.write(row, col, invoice.name or '', data_format)
                    col += 1
                    
                    # COMMERCIAL INVOICE DATE
                    if invoice.invoice_date:
                        sheet.write(row, col, invoice.invoice_date, date_format)
                    col += 1
                    
                    # COMMERCIAL INVOICE AMOUNT
                    sheet.write(row, col, invoice.amount_total or 0.0, number_format)
                    col += 1
                    
                    # CN DATE - empty for commercial invoice row
                    sheet.write(row, col, '', data_format)
                    col += 1
                    
                    # CN NO - empty for commercial invoice row
                    sheet.write(row, col, '', data_format)
                    col += 1
                    
                    # CN AMOUNT - empty for commercial invoice row
                    sheet.write(row, col, '', data_format)
                    col += 1
                    
                    # CN Adjusted Against PI No. - empty
                    sheet.write(row, col, '', data_format)
                    col += 1
                    
                    # Adjustment Amount - empty
                    sheet.write(row, col, '', data_format)
                    col += 1
                    
                    # Balance CN - empty
                    sheet.write(row, col, '', data_format)
                    
                    row += 1
                
                # Create a row for each Credit Note
                for cn in credit_notes:
                    col = 0
                    
                    # PROFORMA INVOICE NO
                    sheet.write(row, col, pi_no, data_format)
                    col += 1
                    
                    # PROFORMA INVOICE DATE
                    if pi_date:
                        sheet.write(row, col, pi_date, date_format)
                    col += 1
                    
                    # PI AMOUNT
                    sheet.write(row, col, pi_amount, number_format)
                    col += 1
                    
                    # COMMERCIAL INVOICE NO
                    # Get the commercial invoice this CN is related to
                    related_invoice = cn.reversed_entry_id if cn.reversed_entry_id else None
                    if not related_invoice and cn.invoice_origin:
                        # Try to find invoice by origin
                        related_invoice = commercial_invoices.filtered(
                            lambda inv: inv.invoice_origin == cn.invoice_origin
                        )[:1]
                    commercial_invoice_no = related_invoice.name if related_invoice else ''
                    sheet.write(row, col, commercial_invoice_no, data_format)
                    col += 1
                    
                    # COMMERCIAL INVOICE DATE
                    if related_invoice and related_invoice.invoice_date:
                        sheet.write(row, col, related_invoice.invoice_date, date_format)
                    else:
                        sheet.write(row, col, '', data_format)
                    col += 1
                    
                    # COMMERCIAL INVOICE AMOUNT
                    if related_invoice:
                        sheet.write(row, col, related_invoice.amount_total or 0.0, number_format)
                    else:
                        sheet.write(row, col, '', data_format)
                    col += 1
                    
                    # CN DATE
                    if cn.invoice_date:
                        sheet.write(row, col, cn.invoice_date, date_format)
                    else:
                        sheet.write(row, col, '', data_format)
                    col += 1
                    
                    # CN NO
                    sheet.write(row, col, cn.name or '', data_format)
                    col += 1
                    
                    # CN AMOUNT
                    cn_amount = abs(cn.amount_total_signed) if cn.amount_total_signed else abs(cn.amount_total) if cn.amount_total else 0.0
                    sheet.write(row, col, cn_amount, number_format)
                    col += 1
                    
                    # CN Adjusted Against PI No.
                    # Determine which PI this CN is adjusted against
                    # If CN has invoice_origin, it's adjusted against that PI
                    adjusted_pi_no = ''
                    if cn.invoice_origin:
                        adjusted_pi_no = cn.invoice_origin
                    elif related_invoice and related_invoice.invoice_origin:
                        adjusted_pi_no = related_invoice.invoice_origin
                    else:
                        # If CN is linked to current order's invoice, use current PI
                        adjusted_pi_no = pi_no
                    sheet.write(row, col, adjusted_pi_no, data_format)
                    col += 1
                    
                    # Adjustment Amount
                    # Calculate how much of this CN is adjusted against the PI
                    # If CN is adjusted against current PI, use full CN amount
                    # Otherwise, check if partially adjusted through reconciliation
                    adjustment_amount = 0.0
                    if adjusted_pi_no == pi_no:
                        # CN is adjusted against current PI
                        # Check if CN is reconciled (fully or partially)
                        if cn.amount_residual == 0:
                            # Fully reconciled/adjusted
                            adjustment_amount = cn_amount
                        else:
                            # Partially adjusted
                            adjustment_amount = cn_amount - abs(cn.amount_residual)
                    elif adjusted_pi_no:
                        # CN is adjusted against a different PI
                        # Check reconciliation status
                        if cn.amount_residual == 0:
                            adjustment_amount = cn_amount
                        else:
                            adjustment_amount = cn_amount - abs(cn.amount_residual)
                    else:
                        # No PI linked, check if CN is reconciled
                        if cn.amount_residual == 0:
                            adjustment_amount = cn_amount
                        else:
                            adjustment_amount = cn_amount - abs(cn.amount_residual)
                    
                    sheet.write(row, col, adjustment_amount, number_format)
                    col += 1
                    
                    # Balance CN
                    # Remaining CN amount after adjustment
                    balance_cn = cn_amount - adjustment_amount
                    sheet.write(row, col, balance_cn, number_format)
                    
                    row += 1
            else:
                # No Commercial Invoices or Credit Notes - just show PI details
                col = 0
                
                # PROFORMA INVOICE NO
                sheet.write(row, col, pi_no, data_format)
                col += 1
                
                # PROFORMA INVOICE DATE
                if pi_date:
                    sheet.write(row, col, pi_date, date_format)
                col += 1
                
                # PI AMOUNT
                sheet.write(row, col, pi_amount, number_format)
                col += 1
                
                # Rest of columns empty
                for _ in range(9):
                    sheet.write(row, col, '', data_format)
                    col += 1
                
                row += 1
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Return base64 encoded content
        return base64.b64encode(output.read())

