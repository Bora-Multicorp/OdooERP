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
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
        tracking=True,
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: fields.Date.today(),
        tracking=True,
    )
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        domain=[('purchase_ok', '=', True)],
        help='Leave empty for all products.',
    )
    brand_id = fields.Many2one('product.brand', string='Brand')
    category_id = fields.Many2one('product.category', string='Category')

    line_ids = fields.One2many(
        'margin.analysis.report',
        'report_id',
        string='Report Lines',
        tracking=True,
    )

    def action_generate_lines(self):
        """Generate report lines: one line per (PO line, MOP record) pair for same product within date range.
        - PO lines: order date between date_from and date_to.
        - MOP records: effective_date between date_from and date_to for same products.
        - Each combination PO line × MOP record (same product) gives one report line.
        - NLC = purchase_rate * 1.18, Funnel = MOP - NLC, % = Funnel/MOP, Total Funnel = Qty * Funnel, x GST = Total/1.18.
        """
        self.ensure_one()
        gst_rate = _get_gst_rate(self.env)  # e.g. 0.18 for 18%
        domain_po = [
            ('order_id.state', 'in', ['purchase', 'done']),
            ('order_id.date_order', '>=', self.date_from),
            ('order_id.date_order', '<=', self.date_to),
        ]
        if self.product_ids:
            domain_po.append(('product_id', 'in', self.product_ids.ids))
        if self.brand_id:
            domain_po.append(('product_id.brand_id', '=', self.brand_id.id))
        if self.category_id:
            domain_po.append(('product_id.categ_id', 'child_of', self.category_id.id))

        po_lines = self.env['purchase.order.line'].search(domain_po, order='order_id, id')
        if not po_lines:
            raise UserError(_('No purchase order lines found for the selected date range and criteria.'))

        product_ids = po_lines.mapped('product_id').ids
        domain_mop = [
            ('product_id', 'in', product_ids),
            ('effective_date', '>=', self.date_from),
            ('effective_date', '<=', self.date_to),
            ('active', '=', True),
        ]
        mop_records = self.env['mop.master'].search(domain_mop, order='product_id, effective_date')

        # Group MOP by product
        mop_by_product = {}
        for mop in mop_records:
            mop_by_product.setdefault(mop.product_id.id, []).append(mop)

        report_lines = []
        for po_line in po_lines:
            product_id = po_line.product_id.id
            po_date = po_line.order_id.date_order.date() if po_line.order_id.date_order else self.date_from
            qty = po_line.product_qty
            purchase_rate = po_line.price_unit or 0.0
            nlc = purchase_rate * (1.0 + gst_rate)

            mop_list = mop_by_product.get(product_id, [])
            if not mop_list:
                # No MOP in range for this product: one line with MOP=0
                report_lines.append({
                    'product_id': product_id,
                    'po_date': po_date,
                    'mop_date': None,
                    'purchase_actual_qty': qty,
                    'purchase_rate': purchase_rate,
                    'nlc': nlc,
                    'mop': 0.0,
                })
            else:
                for mop_rec in mop_list:
                    report_lines.append({
                        'product_id': product_id,
                        'po_date': po_date,
                        'mop_date': mop_rec.effective_date,
                        'purchase_actual_qty': qty,
                        'purchase_rate': purchase_rate,
                        'nlc': nlc,
                        'mop': mop_rec.mop,
                    })

        self.line_ids.unlink()
        for vals in report_lines:
            vals['report_id'] = self.id
            self.env['margin.analysis.report'].create(vals)
        return True


class MarginAnalysisReport(models.Model):
    _name = 'margin.analysis.report'
    _description = 'Funnel Report Line'
    _order = 'product_id, po_date, mop_date'

    product_id = fields.Many2one('product.product', string='Product', required=True, index=True)
    item_name = fields.Char(string='Item Name', related='product_id.name', readonly=True)
    item_alias = fields.Char(string='Item Alias', related='product_id.default_code', readonly=True)

    po_date = fields.Date(string='PO Date', help='Purchase order date for this line', tracking=True)
    mop_date = fields.Date(string='MOP Date', help='MOP effective date for this line', tracking=True)

    purchase_actual_qty = fields.Float(
        string='Purchase Actual Quantity', digits='Product Unit of Measure', tracking=True
    )
    purchase_rate = fields.Float(string='Purchase Rate', digits='Product Price', tracking=True)

    nlc = fields.Float(
        string='NLC',
        digits='Product Price',
        help='NLC = Purchase Rate × 1.18',
        tracking=True,
    )
    mop = fields.Float(
        string='MOP',
        digits='Product Price',
        help='Market Operating Price',
        tracking=True,
    )

    funnal = fields.Float(string='Funnal', digits='Product Price', compute='_compute_funnal', store=True,
                          help='Funnel = MOP - NLC (per unit)')
    funnal_percent = fields.Float(string='%', digits=(12, 2), compute='_compute_funnal', store=True,
                                  help='% = Funnel / MOP')
    total_funnal = fields.Float(string='Total Funnal', digits='Product Price', compute='_compute_total_funnal', store=True,
                                help='Total Funnel = Purchase Actual Qty × Funnel')
    gst_funnal = fields.Float(string='x GST Funnal', digits='Product Price', compute='_compute_gst_funnal', store=True,
                              help='x GST Funnel = Total Funnel / 1.18')

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
        # Funnel (per unit) = MOP - NLC
        # % = Funnel / MOP (as percentage)
        for record in self:
            if record.mop and record.nlc is not None:
                record.funnal = record.mop - record.nlc
                record.funnal_percent = (record.funnal / record.mop * 100.0) if record.mop else 0.0
            else:
                record.funnal = 0.0
                record.funnal_percent = 0.0

    @api.depends('funnal', 'purchase_actual_qty')
    def _compute_total_funnal(self):
        # Total Funnel = Purchase Actual Qty × Funnel
        for record in self:
            record.total_funnal = record.purchase_actual_qty * record.funnal

    @api.depends('total_funnal')
    def _compute_gst_funnal(self):
        # x GST Funnel = Total Funnel / 1.18
        gst_rate = _get_gst_rate(self.env)
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
                record.gst_funnal = record.total_funnal / (1.0 + gst_rate)
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

    report_line_ids = fields.One2many('margin.analysis.report', 'report_id', string='Report Lines')

    def action_generate_report(self):
        """Same logic as header action_generate_lines: PO × MOP within date range."""
        self.ensure_one()
        gst_rate = _get_gst_rate(self.env)
        domain_po = [
            ('order_id.state', 'in', ['purchase', 'done']),
            ('order_id.date_order', '>=', self.date_from),
            ('order_id.date_order', '<=', self.date_to),
        ]
        if self.product_ids:
            domain_po.append(('product_id', 'in', self.product_ids.ids))
        if self.brand_id:
            domain_po.append(('product_id.brand_id', '=', self.brand_id.id))
        if self.category_id:
            domain_po.append(('product_id.categ_id', 'child_of', self.category_id.id))

        po_lines = self.env['purchase.order.line'].search(domain_po, order='order_id, id')
        if not po_lines:
            raise UserError(_('No purchase order lines found for the selected date range and criteria.'))

        product_ids = po_lines.mapped('product_id').ids
        mop_records = self.env['mop.master'].search([
            ('product_id', 'in', product_ids),
            ('effective_date', '>=', self.date_from),
            ('effective_date', '<=', self.date_to),
            ('active', '=', True),
        ], order='product_id, effective_date')
        mop_by_product = {}
        for mop in mop_records:
            mop_by_product.setdefault(mop.product_id.id, []).append(mop)

        report_lines = []
        for po_line in po_lines:
            product_id = po_line.product_id.id
            po_date = po_line.order_id.date_order.date() if po_line.order_id.date_order else self.date_from
            qty = po_line.product_qty
            purchase_rate = po_line.price_unit or 0.0
            nlc = purchase_rate * (1.0 + gst_rate)
            mop_list = mop_by_product.get(product_id, [])
            if not mop_list:
                report_lines.append({
                    'product_id': product_id,
                    'po_date': po_date,
                    'mop_date': None,
                    'purchase_actual_qty': qty,
                    'purchase_rate': purchase_rate,
                    'nlc': nlc,
                    'mop': 0.0,
                })
            else:
                for mop_rec in mop_list:
                    report_lines.append({
                        'product_id': product_id,
                        'po_date': po_date,
                        'mop_date': mop_rec.effective_date,
                        'purchase_actual_qty': qty,
                        'purchase_rate': purchase_rate,
                        'nlc': nlc,
                        'mop': mop_rec.mop,
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
            'res_model': 'margin.analysis.report',
            'view_mode': 'list',
            'domain': [('report_id', '=', self.id)],
            'context': {'search_default_group_by_product': 1},
        }
