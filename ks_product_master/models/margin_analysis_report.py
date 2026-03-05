# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class MarginAnalysisReport(models.TransientModel):
    _name = 'margin.analysis.report'
    _description = 'Funnel'
    _order = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    brand_id = fields.Many2one(
        'product.brand',
        string='Brand',
        related='product_id.product_tmpl_id.brand_id',
        readonly=True,
        store=True,
    )
    item_name = fields.Char(string='Item Name', related='product_id.name', readonly=True)
    item_alias = fields.Char(string='Item Alias', related='product_id.default_code', readonly=True)
    
    purchase_actual_qty = fields.Float(string='Purchase Actual Quantity', digits='Product Unit of Measure')
    purchase_rate = fields.Float(string='Purchase Rate', digits='Product Price')
    
    nlc = fields.Float(string='NLC', digits='Product Price', help='Net Landed Cost')
    mop = fields.Float(string='MOP', digits='Product Price', help='Market Operating Price', readonly=False)
    
    funnal = fields.Float(string='Funnal', digits='Product Price', compute='_compute_funnal')
    funnal_percent = fields.Float(string='%', digits=(12, 2), compute='_compute_funnal')
    
    total_funnal = fields.Float(string='Total Funnal', digits='Product Price', compute='_compute_total_funnal')
    gst_funnal = fields.Float(string='x GST Funnal', digits='Product Price', compute='_compute_gst_funnal')
    
    report_id = fields.Many2one('margin.analysis.report.wizard', string='Report', ondelete='cascade')
    date_from = fields.Date(string='Date From', related='report_id.date_from')
    date_to = fields.Date(string='Date To', related='report_id.date_to')

    @api.depends('mop', 'nlc', 'purchase_actual_qty')
    def _compute_funnal(self):
        """Calculate Funnal = (MOP - NLC) * Quantity"""
        for record in self:
            if record.mop and record.nlc:
                record.funnal = (record.mop - record.nlc) * record.purchase_actual_qty
                # Calculate percentage: ((MOP - NLC) / NLC) * 100
                if record.nlc > 0:
                    record.funnal_percent = ((record.mop - record.nlc) / record.nlc) * 100
                else:
                    record.funnal_percent = 0.0
            else:
                record.funnal = 0.0
                record.funnal_percent = 0.0

    @api.depends('funnal')
    def _compute_total_funnal(self):
        """Total Funnal is same as Funnal for individual line"""
        for record in self:
            record.total_funnal = record.funnal

    @api.depends('total_funnal')
    def _compute_gst_funnal(self):
        """x GST Funnal = Total Funnal / (1 + GST_rate)"""
        for record in self:
            # Get GST rate from company or use default 18%
            company = self.env.company
            gst_rate = 0.18  # Default 18% GST
            # Try to get GST rate from company settings if available
            if hasattr(company, 'gst_rate'):
                gst_rate = company.gst_rate / 100.0 if company.gst_rate else 0.18
            elif hasattr(company, 'vat') and company.vat:
                # Some companies store GST rate in vat field format
                # This is a fallback - adjust based on your setup
                pass
            
            if record.total_funnal:
                record.gst_funnal = record.total_funnal / (1 + gst_rate)
            else:
                record.gst_funnal = 0.0


class MarginAnalysisReportWizard(models.TransientModel):
    _name = 'margin.analysis.report.wizard'
    _description = 'Funnel Wizard'

    name = fields.Char(string='Report Name', default='Funnel')
    date_from = fields.Date(string='Date From', required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(string='Date To', required=True, default=lambda self: fields.Date.today())
    
    product_ids = fields.Many2many('product.product', string='Products', domain=[('purchase_ok', '=', True)])
    brand_id = fields.Many2one('product.brand', string='Brand')
    category_id = fields.Many2one('product.category', string='Category')
    
    report_line_ids = fields.One2many('margin.analysis.report', 'report_id', string='Report Lines')
    
    def action_generate_report(self):
        """Generate the margin analysis report"""
        self.ensure_one()
        
        # Clear existing lines
        self.report_line_ids.unlink()
        
        # Build domain for purchase order lines
        domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
            ('order_id.date_order', '>=', self.date_from),
            ('order_id.date_order', '<=', self.date_to),
        ]
        
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.brand_id:
            domain.append(('product_id.brand_id', '=', self.brand_id.id))
        if self.category_id:
            domain.append(('product_id.categ_id', 'child_of', self.category_id.id))
        
        # Get purchase order lines
        po_lines = self.env['purchase.order.line'].search(domain)
        
        if not po_lines:
            raise UserError(_('No purchase order lines found for the selected criteria.'))
        
        # Group by product and calculate totals
        product_data = {}
        for line in po_lines:
            product = line.product_id
            if product.id not in product_data:
                product_data[product.id] = {
                    'product_id': product.id,
                    'purchase_actual_qty': 0.0,
                    'purchase_rate': 0.0,
                    'total_cost': 0.0,
                }
            
            # Sum quantities and calculate weighted average purchase rate
            qty = line.product_qty
            price = line.price_unit
            
            product_data[product.id]['purchase_actual_qty'] += qty
            product_data[product.id]['total_cost'] += qty * price
        
        # Calculate weighted average purchase rate and get NLC, MOP
        report_lines = []
        for product_id, data in product_data.items():
            product = self.env['product.product'].browse(product_id)
            
            if data['purchase_actual_qty'] > 0:
                avg_purchase_rate = data['total_cost'] / data['purchase_actual_qty']
            else:
                avg_purchase_rate = 0.0
            
            # Get NLC (Net Landed Cost) - using standard_price or purchase rate
            # NLC typically includes all costs (purchase price + landing costs)
            nlc = product.standard_price or avg_purchase_rate
            
            # Get MOP (Market Operating Price) from MOP Master based on date
            # Use date_to from wizard, or today if not available
            mop_date = self.date_to or fields.Date.today()
            mop = self.env['mop.master'].get_current_mop(product_id, mop_date)
            # Fallback to list_price if no MOP Master record found
            if mop is False:
                mop = product.list_price
                # Check if there's a custom MOP field on product
                if 'mop' in product._fields:
                    mop = product.mop or mop
                # Also check product template
                elif 'mop' in product.product_tmpl_id._fields:
                    mop = product.product_tmpl_id.mop or mop
            
            report_lines.append({
                'report_id': self.id,
                'product_id': product_id,
                'purchase_actual_qty': data['purchase_actual_qty'],
                'purchase_rate': avg_purchase_rate,
                'nlc': nlc,
                'mop': mop,
            })
        
        # Create report lines
        self.env['margin.analysis.report'].create(report_lines)
        
        # Return action to view the report
        return {
            'name': _('Funnel'),
            'type': 'ir.actions.act_window',
            'res_model': 'margin.analysis.report',
            'view_mode': 'list',
            'domain': [('report_id', '=', self.id)],
            'context': {'search_default_group_by_product': 1},
        }

