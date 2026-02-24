# -*- coding: utf-8 -*-

import io
from odoo import http, _
from odoo.http import content_disposition, request
from odoo.exceptions import UserError
from odoo.tools.misc import xlsxwriter


class PurchaseOrderReportController(http.Controller):

    @http.route('/purchase_order/export_otek_xlsx', type='http', auth='user', methods=['GET', 'POST'])
    def export_otek_purchase_order_xlsx(self, **kwargs):
        """
        Export Purchase Order lines with Otek brand products to Excel format
        """
        if not xlsxwriter:
            raise UserError(_("xlsxwriter is required for Excel export. Please install it: pip install xlsxwriter"))
        
        # Find the brand "otek"
        brand = request.env['product.brand'].search([('name', '=ilike', 'otek')], limit=1)
        if not brand:
            raise UserError(_("Brand 'otek' not found. Please create the brand first."))
        
        # Get all purchase order lines with products from otek brand
        pol_domain = [
            ('product_id.product_tmpl_id.brand_id', '=', brand.id),
            ('display_type', '=', False),  # Exclude section/note lines
        ]
        pol_lines = request.env['purchase.order.line'].search(pol_domain)
        
        if not pol_lines:
            raise UserError(_("No purchase order lines found with Otek brand products."))
        
        # Create Excel file in memory
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Otek Purchase Order Report')
        
        # Define header format (yellow background, bold, underlined)
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#FFFF00',  # Yellow background
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'underline': True,
        })
        
        # Define cell format
        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter',
        })
        
        # Define number format
        number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        
        # Define headers based on the report format
        headers = [
            'Supplier',
            'Product',
            'Model',
            'Qty',
            'FOB',
            'Amount',
            'Payment',
            'Balance',
            'Payment in INR',
            'IGST',
            'CGST',
            'SGST',
            'CESS',
            'Total Exp',
            'Per PC Landed Cost',
        ]
        
        # Write headers
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, header_format)
        
        # Set column widths
        column_widths = [25, 20, 30, 10, 12, 15, 15, 15, 18, 12, 12, 12, 12, 15, 20]
        for col_num, width in enumerate(column_widths):
            worksheet.set_column(col_num, col_num, width)
        
        # Write data rows
        row_num = 1
        for line in pol_lines:
            order = line.order_id
            product = line.product_id
            product_template = product.product_tmpl_id
            
            # Supplier (Vendor Name)
            supplier = order.partner_id.name if order.partner_id else ''
            worksheet.write(row_num, 0, supplier, cell_format)
            
            # Product (Product category)
            product_category = product_template.categ_id.name if product_template.categ_id else ''
            worksheet.write(row_num, 1, product_category, cell_format)
            
            # Model (Product name)
            model = product_template.name or product.name or ''
            worksheet.write(row_num, 2, model, cell_format)
            
            # Qty (Product qty in POL)
            qty = line.product_qty or 0.0
            worksheet.write(row_num, 3, qty, number_format)
            
            # FOB (Exchange rate - new field on PO)
            fob = order.fob or 0.0
            worksheet.write(row_num, 4, fob, number_format)
            
            # Amount (FOB * QTY)
            amount = fob * qty if fob and qty else 0.0
            worksheet.write(row_num, 5, amount, number_format)
            
            # Payment (Advance payment)
            payment = order.advance_payment or 0.0
            worksheet.write(row_num, 6, payment, number_format)
            
            # Balance (Amount - Payment)
            balance = amount - payment
            worksheet.write(row_num, 7, balance, number_format)
            
            # Payment in INR (Conversion rate * Payment)
            conversion_rate = order.conversion_rate or 1.0
            payment_inr = conversion_rate * payment
            worksheet.write(row_num, 8, payment_inr, number_format)
            
            # Get tax details for the line
            base_line = line._prepare_base_line_for_taxes_computation()
            request.env['account.tax']._add_tax_details_in_base_line(base_line, line.company_id)
            tax_details = base_line.get('tax_details', {})
            taxes_data = tax_details.get('taxes_data', [])
            
            # Initialize tax amounts
            igst = 0.0
            cgst = 0.0
            sgst = 0.0
            cess = 0.0
            
            # Extract individual tax amounts
            for tax_data in taxes_data:
                tax = tax_data.get('tax')
                if tax:
                    # tax is a recordset, get its name
                    tax_name = tax.name.upper() if hasattr(tax, 'name') else ''
                    tax_amount = tax_data.get('tax_amount_currency', 0.0)
                    
                    if 'IGST' in tax_name:
                        igst += tax_amount
                    elif 'CGST' in tax_name:
                        cgst += tax_amount
                    elif 'SGST' in tax_name:
                        sgst += tax_amount
                    elif 'CESS' in tax_name:
                        cess += tax_amount
            
            # IGST
            worksheet.write(row_num, 9, igst, number_format)
            
            # CGST
            worksheet.write(row_num, 10, cgst, number_format)
            
            # SGST
            worksheet.write(row_num, 11, sgst, number_format)
            
            # CESS
            worksheet.write(row_num, 12, cess, number_format)
            
            # Total Exp (Sum of all taxes)
            total_exp = igst + cgst + sgst + cess
            worksheet.write(row_num, 13, total_exp, number_format)
            
            # Per PC Landed Cost ((Total Exp + Payment in INR) / Qty)
            if qty > 0:
                per_pc_landed_cost = (total_exp + payment_inr) / qty
            else:
                per_pc_landed_cost = 0.0
            worksheet.write(row_num, 14, per_pc_landed_cost, number_format)
            
            row_num += 1
        
        # Close workbook
        workbook.close()
        output.seek(0)
        
        # Prepare response
        filename = 'Otek_Purchase_Order_Report.xlsx'
        response = request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        )
        output.close()
        
        return response
