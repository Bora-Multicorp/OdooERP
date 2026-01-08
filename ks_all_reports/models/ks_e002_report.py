# -*- coding: utf-8 -*-

import io
import base64
from odoo import models, api, fields
from odoo.exceptions import UserError
try:
    import xlsxwriter
except ImportError:
    raise UserError('Please install xlsxwriter: pip install xlsxwriter')


class E002Report(models.TransientModel):
    _name = 'ks.e002.report'
    _description = 'E002 Report - Payment and Stock Dispatched Summary'

    file = fields.Binary(string='XLSX File', attachment=True)
    filename = fields.Char(string='Filename', default='E002_Report.xlsx')

    @api.model
    def generate_xlsx_report(self):
        """
        Generate E002 XLSX report with Sale Order payment and stock dispatched data
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
        
        # Create worksheet
        sheet = workbook.add_worksheet('E002 Report')
        
        # Define column headings exactly as specified
        headers = [
            'SR NO.',
            'PARTY NAME',
            'PAYMENT RECEIVED',
            'STOCK DESPATCHED AMOUNT',
            'BALANCE AVALIABLE WITH US',
        ]
        
        # Write headers to first row
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        # Set column widths for better readability
        column_widths = [
            10,  # SR NO.
            30,  # PARTY NAME
            20,  # PAYMENT RECEIVED
            25,  # STOCK DESPATCHED AMOUNT
            25,  # BALANCE AVALIABLE WITH US
        ]
        
        # Apply column widths
        for col, width in enumerate(column_widths):
            sheet.set_column(col, col, width)
        
        # Freeze first row
        sheet.freeze_panes(1, 0)
        
        # Get eligible Sale Orders: confirmed (state = 'sale') with at least one payment
        sale_orders = self._get_eligible_sale_orders()
        
        # Process each Sale Order
        row = 1
        sr_no = 1
        for order in sale_orders:
            # SR NO.
            sheet.write(row, 0, sr_no, data_format)
            
            # PARTY NAME - Sale Order customer name
            party_name = order.partner_id.name if order.partner_id else ''
            sheet.write(row, 1, party_name, data_format)
            
            # PAYMENT RECEIVED - Total amount of payments received
            payment_received, _, _, _ = self._get_payment_info(order)
            sheet.write(row, 2, payment_received, number_format)
            
            # STOCK DESPATCHED AMOUNT - Total amount of completed deliveries (done pickings)
            stock_dispatched_amount = self._get_stock_dispatched_amount(order)
            sheet.write(row, 3, stock_dispatched_amount, number_format)
            
            # BALANCE AVALIABLE WITH US - PAYMENT RECEIVED - STOCK DESPATCHED AMOUNT
            # Ensure negative values are not shown (set to 0 if negative)
            balance_available = payment_received - stock_dispatched_amount
            if balance_available < 0:
                balance_available = 0.0
            sheet.write(row, 4, balance_available, number_format)
            
            row += 1
            sr_no += 1
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Return base64 encoded content
        return base64.b64encode(output.read())
    
    def _get_eligible_sale_orders(self):
        """
        Get Sale Orders that meet the E002 report criteria:
        - Must be confirmed (state = 'sale')
        - Must have at least one payment received
        """
        # Get all confirmed Sale Orders
        confirmed_orders = self.env['sale.order'].search([
            ('state', '=', 'sale')
        ])
        
        # Filter to only include orders with at least one payment
        eligible_orders = self.env['sale.order']
        
        for order in confirmed_orders:
            if self._has_payment_received(order):
                eligible_orders |= order
        
        return eligible_orders
    
    def _has_payment_received(self, order):
        """
        Check if a Sale Order has at least one payment received.
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
            if hasattr(invoice, 'reconciled_payment_ids'):
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
    
    def _get_stock_dispatched_amount(self, order):
        """
        Calculate total stock dispatched amount for a Sale Order.
        This is the total value of completed deliveries (done pickings).
        Calculated as: sum of (qty_delivered * price_unit) for all order lines
        """
        total_dispatched_amount = 0.0
        
        # Calculate based on delivered quantities from order lines
        for line in order.order_line:
            if line.qty_delivered > 0:
                # Value = delivered quantity * unit price
                total_dispatched_amount += line.qty_delivered * line.price_unit
        
        return total_dispatched_amount

