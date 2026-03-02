# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta

# Default GST rate (e.g. 18%) for NLC = purchase_rate * (1 + GST rate)
DEFAULT_GST_RATE = 0.18


def _get_gst_rate(env):
    """Return GST rate as decimal (e.g. 0.18 for 18%)."""
    company = env.company
    if hasattr(company, 'gst_rate') and company.gst_rate:
        return float(company.gst_rate) / 100.0
    return DEFAULT_GST_RATE


class MarginAnalysisReportHeader(models.Model):
    _name = 'margin.analysis.report.header'
    _description = 'Funnel Report (Master)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, id desc'

    name = fields.Char(string='Report Name', required=True, default='Funnel', tracking=True)
    date_from = fields.Date(string='Date From', required=True, tracking=True)
    date_to = fields.Date(string='Date To', required=True, tracking=True)
    line_ids = fields.One2many(
        'margin.analysis.report',
        'report_id',
        string='Report Lines',
        tracking=True,
    )


class MarginAnalysisReport(models.Model):
    _name = 'margin.analysis.report'
    _description = 'Funnel Report Line'
    _order = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', required=True, index=True, tracking=True)
    item_name = fields.Char(string='Item Name', related='product_id.name', readonly=True)
    item_alias = fields.Char(string='Item Alias', related='product_id.default_code', readonly=True)

    purchase_actual_qty = fields.Float(
        string='Purchase Actual Quantity', digits='Product Unit of Measure', tracking=True
    )
    purchase_rate = fields.Float(string='Purchase Rate', digits='Product Price', tracking=True)

    nlc = fields.Float(
        string='NLC',
        digits='Product Price',
        help='Net Landed Cost = Purchase Rate × (1 + GST rate)',
        tracking=True,
    )
    mop = fields.Float(
        string='MOP',
        digits='Product Price',
        help='Market Operating Price',
        tracking=True,
    )

    funnal = fields.Float(string='Funnal', digits='Product Price', compute='_compute_funnal', store=True)
    funnal_percent = fields.Float(string='%', digits=(12, 2), compute='_compute_funnal', store=True)

    total_funnal = fields.Float(string='Total Funnal', digits='Product Price', compute='_compute_total_funnal', store=True)
    gst_funnal = fields.Float(string='x GST Funnal', digits='Product Price', compute='_compute_gst_funnal', store=True)

    report_id = fields.Many2one(
        'margin.analysis.report.header',
        string='Report',
        ondelete='cascade',
        required=True,
        index=True,
        tracking=True,
    )
    date_from = fields.Date(string='Date From', related='report_id.date_from', store=True)
    date_to = fields.Date(string='Date To', related='report_id.date_to', store=True)

    def write(self, vals):
        res = super().write(vals)
        if vals and res:
            labels = []
            for k in vals:
                if k in self._fields and k != 'report_id':
                    labels.append(self._fields[k].string)
            if labels:
                for line in self:
                    if line.report_id:
                        line.report_id.message_post(
                            body=_('Funnel line updated (%s): %s') % (line.item_name or line.product_id.name, ', '.join(labels)),
                            message_type='notification',
                        )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.report_id:
                line.report_id.message_post(
                    body=_('Funnel line added: %s') % (line.item_name or line.product_id.name),
                    message_type='notification',
                )
        return lines

    def unlink(self):
        headers = self.report_id
        res = super().unlink()
        for header in headers:
            if header.exists():
                header.message_post(
                    body=_('Funnel line(s) removed'),
                    message_type='notification',
                )
        return res

    @api.depends('mop', 'nlc', 'purchase_actual_qty')
    def _compute_funnal(self):
        for record in self:
            if record.mop and record.nlc:
                record.funnal = (record.mop - record.nlc) * record.purchase_actual_qty
                if record.nlc > 0:
                    record.funnal_percent = ((record.mop - record.nlc) / record.nlc) * 100
                else:
                    record.funnal_percent = 0.0
            else:
                record.funnal = 0.0
                record.funnal_percent = 0.0

    @api.depends('funnal')
    def _compute_total_funnal(self):
        for record in self:
            record.total_funnal = record.funnal

    @api.depends('total_funnal')
    def _compute_gst_funnal(self):
        gst_rate = _get_gst_rate(self.env)
        for record in self:
            if record.total_funnal:
                record.gst_funnal = record.total_funnal / (1 + gst_rate)
            else:
                record.gst_funnal = 0.0


class MarginAnalysisReportWizard(models.TransientModel):
    _name = 'margin.analysis.report.wizard'
    _description = 'Funnel Wizard'

    name = fields.Char(string='Report Name', default='Funnel')
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        help='Back date and future date are allowed.',
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: fields.Date.today(),
        help='Back date and future date are allowed.',
    )

    product_ids = fields.Many2many('product.product', string='Products', domain=[('purchase_ok', '=', True)])
    brand_id = fields.Many2one('product.brand', string='Brand')
    category_id = fields.Many2one('product.category', string='Category')

    def action_generate_report(self):
        self.ensure_one()

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

        po_lines = self.env['purchase.order.line'].search(domain)

        if not po_lines:
            raise UserError(_('No purchase order lines found for the selected criteria.'))

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
            qty = line.product_qty
            price = line.price_unit
            product_data[product.id]['purchase_actual_qty'] += qty
            product_data[product.id]['total_cost'] += qty * price

        gst_rate = _get_gst_rate(self.env)
        report_lines = []
        for product_id, data in product_data.items():
            product = self.env['product.product'].browse(product_id)

            if data['purchase_actual_qty'] > 0:
                avg_purchase_rate = data['total_cost'] / data['purchase_actual_qty']
            else:
                avg_purchase_rate = 0.0

            # NLC = Purchase Rate × (1 + GST rate)
            nlc = avg_purchase_rate * (1 + gst_rate)

            # MOP from MOP Master only (by report date_to)
            mop_date = self.date_to or fields.Date.today()
            mop = self.env['mop.master'].get_current_mop(product_id, mop_date)
            if mop is False:
                mop = 0.0

            report_lines.append({
                'product_id': product_id,
                'purchase_actual_qty': data['purchase_actual_qty'],
                'purchase_rate': avg_purchase_rate,
                'nlc': nlc,
                'mop': mop,
            })

        header = self.env['margin.analysis.report.header'].create({
            'name': self.name or 'Funnel',
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        for vals in report_lines:
            vals['report_id'] = header.id
            self.env['margin.analysis.report'].create(vals)

        return {
            'name': _('Funnel'),
            'type': 'ir.actions.act_window',
            'res_model': 'margin.analysis.report.header',
            'res_id': header.id,
            'view_mode': 'form',
            'target': 'current',
        }
