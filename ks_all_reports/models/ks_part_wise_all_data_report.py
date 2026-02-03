# -*- coding: utf-8 -*-

import io
import base64
from odoo import models, api, fields
from odoo.exceptions import UserError
try:
    import xlsxwriter
except ImportError:
    raise UserError('Please install xlsxwriter: pip install xlsxwriter')


class PartWiseAllDataReport(models.TransientModel):
    _name = 'ks.part.wise.all.data.report'
    _description = 'Part Wise All Data Report'

    file = fields.Binary(string='XLSX File', attachment=True)
    filename = fields.Char(string='Filename', default='Part_Wise_All_Data.xlsx')

    @api.model
    def generate_xlsx_report(self):
        """
        Generate XLSX report with Sale Order data
        Each Sale Order gets its own sheet
        Returns base64 encoded file content
        """
        # Create output in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Define header style with bold text and light background
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',  # Light gray background
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
        
        # Define date format
        date_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy',
        })
        
        # Define datetime format (for datetime fields)
        datetime_format = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': 'dd/mm/yyyy hh:mm:ss',
        })
        
        # Define column headings in exact order as specified
        headers = [
            'PROFORMA INVOICE NO',
            'PROFORMA INVOICE DATE',
            'MODEL',
            'COLOR',
            'QTY',
            'RATE (INR)',
            'PI AMOUNT',
            'TOTAL AMOUNT',
            'PAYMENT RECEIVED',
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
            'REMARKS 1',
            'REMARKS 2',
            'DIFFERENCE FUNDS TO INVOICE',
            'FUNDS BALANCE / RECEIVABLE AGAINST PI',
            'BALANCE QTY',
            'VALUE',
            'REMARKS',
        ]
        
        # Set column widths
        column_widths = [
            20,  # PROFORMA INVOICE NO
            18,  # PROFORMA INVOICE DATE
            15,  # MODEL
            12,  # COLOR
            10,  # QTY
            12,  # RATE (INR)
            12,  # PI AMOUNT
            12,  # TOTAL AMOUNT
            15,  # PAYMENT RECEIVED
            15,  # PAYMENT DATE
            12,  # BALANCE
            15,  # BANK NAME
            12,  # AD CODE
            15,  # DESPATCHED QTY
            12,  # PENDING QTY
            15,  # DESPATCHED DATE
            20,  # COMMERCIAL INVOICES
            20,  # DISPATCHED GOODS VALUE
            35,  # TOTAL STOCK VALUE DISPATCHED AGAINST PI
            35,  # STOCK VALUE TO BE DISPATCHED AGAINST PI
            15,  # REMARKS 1
            15,  # REMARKS 2
            25,  # DIFFERENCE FUNDS TO INVOICE
            35,  # FUNDS BALANCE / RECEIVABLE AGAINST PI
            12,  # BALANCE QTY
            12,  # VALUE
            20,  # REMARKS
        ]
        
        # Fetch Sale Orders that meet the criteria:
        # 1. Must be confirmed (state = 'sale')
        # 2. Must have advance payment (partially paid, fully paid, or advance/down payment)
        sale_orders = self._get_eligible_sale_orders()
        
        # Process each Sale Order - one sheet per order
        for order in sale_orders:
            # Create worksheet for this Sale Order (limit sheet name to 31 chars)
            sheet_name = order.name[:31] if order.name else f"SO_{order.id}"
            sheet = workbook.add_worksheet(sheet_name)
            
            # Write headers to first row
            for col, header in enumerate(headers):
                sheet.write(0, col, header, header_format)
            
            # Apply column widths
            for col, width in enumerate(column_widths):
                sheet.set_column(col, col, width)
            
            # Freeze first row
            sheet.freeze_panes(1, 0)
            
            # Get order-level data (same for all lines)
            proforma_invoice_no = order.name or ''
            proforma_invoice_date = order.create_date if order.create_date else False
            pi_amount = order.amount_total or 0.0
            total_amount = order.amount_total or 0.0
            
            # Get payment information
            payment_received, payment_dates, bank_names, bank_codes = self._get_payment_info(order)
            balance = total_amount - payment_received
            
            # Get invoice information
            commercial_invoices = ', '.join(order.invoice_ids.mapped('name')) if order.invoice_ids else ''
            invoiced_amount = sum(order.invoice_ids.filtered(lambda inv: inv.state == 'posted').mapped('amount_total')) if order.invoice_ids else 0.0
            # DIFFERENCE FUNDS TO INVOICE = Sale Order total amount - Total invoiced amount
            difference_funds_to_invoice = total_amount - invoiced_amount
            funds_balance = total_amount - payment_received
            
            # Get picking information
            pickings = self.env['stock.picking'].search([
                ('sale_id', '=', order.id),
                ('state', '=', 'done')
            ])
            dispatched_dates_list = []
            for picking in pickings:
                if picking.date_done:
                    date_str = picking.date_done.strftime('%d/%m/%Y')
                    if date_str not in dispatched_dates_list:
                        dispatched_dates_list.append(date_str)
            dispatched_dates = ', '.join(dispatched_dates_list) if dispatched_dates_list else ''
            
            # Calculate dispatched values
            total_dispatched_value = 0.0
            for line in order.order_line:
                if line.qty_delivered > 0:
                    total_dispatched_value += line.qty_delivered * line.price_unit
            
            stock_value_to_dispatch = total_amount - total_dispatched_value
            
            # Process each order line
            row = 1
            for line in order.order_line.filtered(lambda l: not l.display_type):
                # PROFORMA INVOICE NO
                sheet.write(row, 0, proforma_invoice_no, data_format)
                
                # PROFORMA INVOICE DATE
                if proforma_invoice_date:
                    # Write datetime directly - xlsxwriter will format it
                    sheet.write_datetime(row, 1, proforma_invoice_date, date_format)
                else:
                    sheet.write(row, 1, '', data_format)
                
                # MODEL
                model = line.product_id.name if line.product_id else ''
                sheet.write(row, 2, model, data_format)
                
                # COLOR
                sheet.write(row, 3, '', data_format)  # Empty for now
                
                # QTY
                qty = line.product_uom_qty or 0.0
                sheet.write(row, 4, qty, number_format)
                
                # RATE (INR)
                rate = line.price_unit or 0.0
                sheet.write(row, 5, rate, number_format)
                
                # PI AMOUNT
                sheet.write(row, 6, pi_amount, number_format)
                
                # TOTAL AMOUNT
                sheet.write(row, 7, total_amount, number_format)
                
                # PAYMENT RECEIVED
                sheet.write(row, 8, payment_received, number_format)
                
                # PAYMENT DATE
                sheet.write(row, 9, payment_dates, data_format)
                
                # BALANCE
                sheet.write(row, 10, balance, number_format)
                
                # BANK NAME
                sheet.write(row, 11, bank_names, data_format)
                
                # AD CODE - Bank short code from journal
                sheet.write(row, 12, bank_codes, data_format)
                
                # DESPATCHED QTY
                dispatched_qty = line.qty_delivered or 0.0
                sheet.write(row, 13, dispatched_qty, number_format)
                
                # PENDING QTY
                pending_qty = qty - dispatched_qty
                sheet.write(row, 14, pending_qty, number_format)
                
                # DESPATCHED DATE
                sheet.write(row, 15, dispatched_dates, data_format)
                
                # COMMERCIAL INVOICES
                sheet.write(row, 16, commercial_invoices, data_format)
                
                # DISPATCHED GOODS VALUE - Total value of goods dispatched (based on delivered quantity)
                dispatched_goods_value = dispatched_qty * rate
                sheet.write(row, 17, dispatched_goods_value, number_format)
                
                # TOTAL STOCK VALUE DISPATCHED AGAINST PI
                sheet.write(row, 18, total_dispatched_value, number_format)
                
                # STOCK VALUE TO BE DISPATCHED AGAINST PI
                sheet.write(row, 19, stock_value_to_dispatch, number_format)
                
                # REMARKS 1
                sheet.write(row, 20, '', data_format)
                
                # REMARKS 2
                sheet.write(row, 21, '', data_format)
                
                # DIFFERENCE FUNDS TO INVOICE
                sheet.write(row, 22, difference_funds_to_invoice, number_format)
                
                # FUNDS BALANCE / RECEIVABLE AGAINST PI
                sheet.write(row, 23, funds_balance, number_format)
                
                # BALANCE QTY
                sheet.write(row, 24, pending_qty, number_format)
                
                # VALUE
                balance_value = pending_qty * rate
                sheet.write(row, 25, balance_value, number_format)
                
                # REMARKS
                sheet.write(row, 26, '', data_format)
                
                row += 1
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Return base64 encoded content
        return base64.b64encode(output.read())
    
    def _get_payment_info(self, order):
        """
        Get payment information for a Sale Order
        Returns: (total_paid, payment_dates, bank_names, bank_codes)
        """
        total_paid = 0.0
        payment_dates = []
        bank_names = []
        bank_codes = []
        
        # Get payments from invoices
        invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
        for invoice in invoices:
            # Get payments reconciled to this invoice
            # Use reconciled_payment_ids if available, otherwise search
            if hasattr(invoice, 'reconciled_payment_ids'):
                # Filter for posted or paid payments
                payments = invoice.reconciled_payment_ids.filtered(
                    lambda p: p.state in ('posted', 'paid')
                )
            else:
                # Fallback: search for payments reconciled to this invoice
                payments = self.env['account.payment'].search([
                    ('state', 'in', ('posted', 'paid')),
                    ('reconciled_invoice_ids', 'in', invoice.ids)
                ])
            
            for payment in payments:
                total_paid += payment.amount
                if payment.date:
                    date_str = payment.date.strftime('%d/%m/%Y')
                    if date_str not in payment_dates:
                        payment_dates.append(date_str)
                # Get bank name and code from journal if it's a bank payment
                if payment.journal_id and payment.journal_id.type == 'bank':
                    bank_name = payment.journal_id.name or ''
                    if bank_name and bank_name not in bank_names:
                        bank_names.append(bank_name)
                    # Get bank short code (AD CODE)
                    bank_code = payment.journal_id.code or ''
                    if bank_code and bank_code not in bank_codes:
                        bank_codes.append(bank_code)
        
        # Also check for advance payments if the module exists
        if hasattr(order, 'ks_advance_payment_ids'):
            for payment in order.ks_advance_payment_ids.filtered(lambda p: p.state in ('posted', 'paid')):
                total_paid += payment.amount
                if payment.date:
                    date_str = payment.date.strftime('%d/%m/%Y')
                    if date_str not in payment_dates:
                        payment_dates.append(date_str)
                if payment.journal_id and payment.journal_id.type == 'bank':
                    bank_name = payment.journal_id.name or ''
                    if bank_name and bank_name not in bank_names:
                        bank_names.append(bank_name)
                    # Get bank short code (AD CODE)
                    bank_code = payment.journal_id.code or ''
                    if bank_code and bank_code not in bank_codes:
                        bank_codes.append(bank_code)
        
        payment_dates_str = ', '.join(payment_dates) if payment_dates else ''
        bank_names_str = ', '.join(bank_names) if bank_names else ''
        bank_codes_str = ', '.join(bank_codes) if bank_codes else ''
        
        return total_paid, payment_dates_str, bank_names_str, bank_codes_str
    
    def _get_eligible_sale_orders(self):
        """
        Get Sale Orders that meet the report criteria:
        - Must be confirmed (state = 'sale')
        - Must have advance payment created against them (partially paid, fully paid, or advance/down payment)
        - Excludes: quotation, draft, cancelled, or unpaid orders
        """
        # First, get all confirmed Sale Orders
        confirmed_orders = self.env['sale.order'].search([
            ('state', '=', 'sale')
        ])
        
        # Filter to only include orders with advance payments
        eligible_orders = self.env['sale.order']
        
        for order in confirmed_orders:
            if self._has_advance_payment(order):
                eligible_orders |= order
        
        return eligible_orders
    
    def _has_advance_payment(self, order):
        """
        Check if a Sale Order has any advance payment.
        Advance payment means:
        - Advance payments linked via ks_advance_payment_ids (if module exists)
        - Payments reconciled to invoices
        - Partially paid, fully paid, or advance/down payment
        Returns True if order has any payment, False otherwise.
        """
        # Check for advance payments via ks_advance_payment_ids (if module exists)
        if hasattr(order, 'ks_advance_payment_ids'):
            advance_payments = order.ks_advance_payment_ids.filtered(
                lambda p: p.state in ('posted', 'paid')
            )
            if advance_payments:
                return True
        
        # Check for payments via invoices
        invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
        if invoices:
            # Check if any invoice has reconciled payments
            for invoice in invoices:
                if hasattr(invoice, 'reconciled_payment_ids'):
                    payments = invoice.reconciled_payment_ids.filtered(
                        lambda p: p.state in ('posted', 'paid')
                    )
                    if payments:
                        return True
                else:
                    # Fallback: search for payments reconciled to this invoice
                    payments = self.env['account.payment'].search([
                        ('state', 'in', ('posted', 'paid')),
                        ('reconciled_invoice_ids', 'in', invoice.ids)
                    ])
                    if payments:
                        return True
        
        # Check for direct payments linked to sale order (if field exists)
        if hasattr(order, 'payment_ids'):
            payments = order.payment_ids.filtered(
                lambda p: p.state in ('posted', 'paid')
            )
            if payments:
                return True
        
        # Check for payment transactions (online payments)
        if hasattr(order, 'transaction_ids'):
            transactions = order.transaction_ids.filtered(
                lambda t: t.state in ('done', 'authorized')
            )
            if transactions:
                return True
        
        return False

