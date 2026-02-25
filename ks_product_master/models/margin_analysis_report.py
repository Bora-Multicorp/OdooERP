# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_round
from datetime import datetime, timedelta


class MarginAnalysisReport(models.TransientModel):
    _name = 'margin.analysis.report'
    _description = 'Funnel'
    _order = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    item_name = fields.Char(string='Item Name', related='product_id.name', readonly=True)
    item_alias = fields.Char(string='Item Alias', related='product_id.default_code', readonly=True)
    
    purchase_actual_qty = fields.Float(string='Purchase Actual Quantity', digits='Product Unit of Measure')
    purchase_rate = fields.Float(string='Purchase Rate', digits='Product Price')
    
    nlc = fields.Float(string='NLC', digits='Product Price', help='Net Landed Cost (Purchase Rate incl. 18%% GST)')
    mop = fields.Float(string='MOP', digits='Product Price', help='Market Operating Price', readonly=False)
    
    funnal = fields.Float(string='Funnal', digits='Product Price', compute='_compute_funnal', help='MOP - NLC (per unit)')
    funnal_percent = fields.Float(string='%', digits=(12, 2), compute='_compute_funnal', help='Funnal / MOP')
    
    total_funnal = fields.Float(string='Total Funnal', digits='Product Price', compute='_compute_total_funnal', help='Purchase Qty * Funnal')
    gst_funnal = fields.Float(string='x GST Funnal', digits='Product Price', compute='_compute_gst_funnal', help='Total Funnal / 1.18')
    
    report_id = fields.Many2one('margin.analysis.report.wizard', string='Report', ondelete='cascade')
    date_from = fields.Date(string='Date From', related='report_id.date_from')
    date_to = fields.Date(string='Date To', related='report_id.date_to')

    @api.depends('mop', 'nlc')
    def _compute_funnal(self):
        """Funnal = MOP - NLC (per unit). % = Funnal / MOP"""
        for record in self:
            if record.mop is not False and record.nlc is not False:
                record.funnal = record.mop - record.nlc
                # Percentage: Funnal / MOP (as per formula =G4/F4)
                if record.mop and record.mop != 0:
                    record.funnal_percent = (record.funnal / record.mop) * 100
                else:
                    record.funnal_percent = 0.0
            else:
                record.funnal = 0.0
                record.funnal_percent = 0.0

    @api.depends('funnal', 'purchase_actual_qty')
    def _compute_total_funnal(self):
        """Total Funnal = Purchase Actual Quantity * Funnal (as per formula =C4*G4)"""
        for record in self:
            record.total_funnal = (record.purchase_actual_qty or 0.0) * (record.funnal or 0.0)

    @api.depends('total_funnal')
    def _compute_gst_funnal(self):
        """x GST Funnal = Total Funnal / 1.18 (as per formula =I4/1.18)"""
        for record in self:
            if record.total_funnal:
                record.gst_funnal = record.total_funnal / 1.18
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
            
            # NLC = Incl GST price of that SKU (as per formula =D4*1.18).
            # Prefer product cost from inventory master; else use Purchase Rate from PO. Then add 18% GST.
            cost_excl_gst = product.standard_price or avg_purchase_rate or 0.0
            rounding = self.env['decimal.precision'].precision_get('Product Price')
            nlc = float_round(cost_excl_gst * 1.18, precision_digits=rounding)
            
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

