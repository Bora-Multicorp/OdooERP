# -*- coding: utf-8 -*-

import io
import base64
from odoo import models, api
from odoo.exceptions import UserError
try:
    import xlsxwriter
except ImportError:
    raise UserError('Please install xlsxwriter: pip install xlsxwriter')


class PartWiseAllDataReport(models.TransientModel):
    _name = 'ks.part.wise.all.data.report'
    _description = 'Part Wise All Data Report'

    def generate_xlsx_report(self):
        """
        Generate XLSX report with column headings only
        Returns base64 encoded file content
        """
        # Create output in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        
        # Create worksheet
        sheet = workbook.add_worksheet('Part Wise All Data')
        
        # Define header style with bold text and light background
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',  # Light gray background
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
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
        
        # Write headers to first row
        for col, header in enumerate(headers):
            sheet.write(0, col, header, header_format)
        
        # Set column widths for better readability
        # Adjust widths based on header text length
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
        
        # Apply column widths
        for col, width in enumerate(column_widths):
            sheet.set_column(col, col, width)
        
        # Freeze first row
        sheet.freeze_panes(1, 0)
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Return base64 encoded content
        return base64.b64encode(output.read())

