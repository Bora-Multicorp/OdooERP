# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AdMarginReport(models.TransientModel):
    _name = 'ad.margin.report'
    _description = 'AD Margin Report'
    _order = 'partner_id, product_id'

    partner_id = fields.Many2one('res.partner', string='Party Name', required=True, index=True)
    party_name = fields.Char(string='Party Name', related='partner_id.name', readonly=True)
    
    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    item_name = fields.Char(string='Item Name', related='product_id.name', readonly=True)
    item_alias = fields.Char(string='Item', related='product_id.default_code', readonly=True)
    
    sales_rate = fields.Float(string='Sales Rate', digits='Product Price')
    sales_quantity = fields.Float(string='Sales Quantity', digits='Product Unit of Measure')
    
    mop = fields.Float(string='MOP', digits='Product Price', help='Market Operating Price')
    x_gst_mop = fields.Float(string='X GST MC', digits='Product Price', compute='_compute_x_gst_mop')
    diff = fields.Float(string='Diff', digits='Product Price', compute='_compute_diff')
    margin = fields.Float(string='Margin', digits=(12, 2), compute='_compute_margin')
    total = fields.Float(string='Total', digits='Product Price', compute='_compute_total')
    
    report_id = fields.Many2one('ad.margin.report.wizard', string='Report', ondelete='cascade')
    invoice_date = fields.Date(string='Invoice Date', related='invoice_id.invoice_date', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)

    @api.depends('mop')
    def _compute_x_gst_mop(self):
        """X GST MC = MOP / 1.18 (MOP excluding GST, as per formula)"""
        for record in self:
            if record.mop:
                record.x_gst_mop = record.mop / 1.18
            else:
                record.x_gst_mop = 0.0

    @api.depends('sales_rate', 'x_gst_mop')
    def _compute_diff(self):
        """Diff = X GST MC - Sales Rate (Item), as per formula =G3-D3"""
        for record in self:
            record.diff = (record.x_gst_mop or 0.0) - (record.sales_rate or 0.0)

    @api.depends('diff', 'x_gst_mop')
    def _compute_margin(self):
        """Margin = Diff / X GST MC, as per formula =H3/G3 (stored as percentage)"""
        for record in self:
            if record.x_gst_mop and record.x_gst_mop != 0:
                record.margin = (record.diff / record.x_gst_mop) * 100
            else:
                record.margin = 0.0

    @api.depends('diff', 'sales_quantity')
    def _compute_total(self):
        """Total = Diff * Sales Quantity, as per formula =H3*E3"""
        for record in self:
            record.total = (record.diff or 0.0) * (record.sales_quantity or 0.0)


class AdMarginReportWizard(models.TransientModel):
    _name = 'ad.margin.report.wizard'
    _description = 'AD Margin Report Wizard'

    name = fields.Char(string='Report Name', default='AD Margin Report')
    date_from = fields.Date(string='Date From', required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Date To', required=True, default=lambda self: fields.Date.today())
    
    partner_ids = fields.Many2many('res.partner', string='Customers', domain=[('is_company', '=', True)])
    product_ids = fields.Many2many('product.product', string='Products')
    brand_id = fields.Many2one('product.brand', string='Brand')
    category_id = fields.Many2one('product.category', string='Category')
    
    report_line_ids = fields.One2many('ad.margin.report', 'report_id', string='Report Lines')
    
    def action_generate_report(self):
        """Generate the AD Margin report from sales invoices"""
        self.ensure_one()
        
        # Clear existing lines
        self.report_line_ids.unlink()
        
        # Build domain for invoice lines
        domain = [
            ('move_id.move_type', '=', 'out_invoice'),  # Customer invoices only
            ('move_id.state', '=', 'posted'),  # Posted invoices only
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('product_id', '!=', False),  # Only product lines
        ]
        
        if self.partner_ids:
            domain.append(('move_id.partner_id', 'in', self.partner_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.brand_id:
            domain.append(('product_id.brand_id', '=', self.brand_id.id))
        if self.category_id:
            domain.append(('product_id.categ_id', 'child_of', self.category_id.id))
        
        # Get invoice lines
        invoice_lines = self.env['account.move.line'].search(domain)
        
        if not invoice_lines:
            raise UserError(_('No invoice lines found for the selected criteria.'))
        
        # Group by partner and product
        report_data = {}
        for line in invoice_lines:
            partner = line.move_id.partner_id
            product = line.product_id
            key = (partner.id, product.id)
            
            if key not in report_data:
                report_data[key] = {
                    'partner_id': partner.id,
                    'product_id': product.id,
                    'sales_rate': 0.0,
                    'sales_quantity': 0.0,
                    'total_amount': 0.0,
                    'invoice_id': line.move_id.id,
                }
            
            # Sum quantities and calculate weighted average sales rate
            qty = line.quantity
            price = line.price_unit
            
            report_data[key]['sales_quantity'] += qty
            report_data[key]['total_amount'] += qty * price
        
        # Calculate weighted average sales rate and get MOP
        report_lines = []
        for (partner_id, product_id), data in report_data.items():
            product = self.env['product.product'].browse(product_id)
            
            if data['sales_quantity'] > 0:
                avg_sales_rate = data['total_amount'] / data['sales_quantity']
            else:
                avg_sales_rate = 0.0
            
            # Get MOP (Market Operating Price) from MOP Master based on invoice date
            invoice = self.env['account.move'].browse(data['invoice_id'])
            invoice_date = invoice.invoice_date or fields.Date.today()
            mop = self.env['mop.master'].get_current_mop(product_id, invoice_date)
            # Fallback to list_price if no MOP Master record found
            if mop is False:
                mop = product.list_price
                # Check if there's a custom MOP field
                if 'mop' in product._fields:
                    mop = product.mop or mop
                elif 'mop' in product.product_tmpl_id._fields:
                    mop = product.product_tmpl_id.mop or mop
            
            report_lines.append({
                'report_id': self.id,
                'partner_id': partner_id,
                'product_id': product_id,
                'sales_rate': avg_sales_rate,
                'sales_quantity': data['sales_quantity'],
                'mop': mop,
                'invoice_id': data['invoice_id'],
            })
        
        # Create report lines
        self.env['ad.margin.report'].create(report_lines)
        
        # Return action to view the report
        return {
            'name': _('AD Margin Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'ad.margin.report',
            'view_mode': 'list',
            'domain': [('report_id', '=', self.id)],
            'context': {'search_default_group_by_partner': 1},
        }

