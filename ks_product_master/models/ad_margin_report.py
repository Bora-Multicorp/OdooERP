# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AdMarginReportHeader(models.Model):
    _name = 'ad.margin.report.header'
    _description = 'AD Margin Report (Master)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, id desc'

    name = fields.Char(string='Report Name', required=True, default='AD Margin Report', tracking=True)
    date_from = fields.Date(string='Date From', required=True, tracking=True)
    date_to = fields.Date(string='Date To', required=True, tracking=True)
    line_ids = fields.One2many(
        'ad.margin.report',
        'report_id',
        string='Report Lines',
        tracking=True,
    )


class AdMarginReport(models.Model):
    _name = 'ad.margin.report'
    _description = 'AD Margin Report Line'
    _order = 'partner_id, product_id'

    partner_id = fields.Many2one('res.partner', string='Party Name', required=True, index=True, tracking=True)
    party_name = fields.Char(string='Party', related='partner_id.name', readonly=True)

    product_id = fields.Many2one('product.product', string='Product', required=True, index=True, tracking=True)
    item_name = fields.Char(string='Item Name', related='product_id.name', readonly=True)
    item_alias = fields.Char(string='Item', related='product_id.default_code', readonly=True)

    sales_rate = fields.Float(string='Sales Rate', digits='Product Price', tracking=True)
    sales_quantity = fields.Float(string='Sales Quantity', digits='Product Unit of Measure', tracking=True)

    mop = fields.Float(string='MOP', digits='Product Price', help='Market Operating Price', tracking=True)
    x_gst_mop = fields.Float(string='X GST MO', digits='Product Price', compute='_compute_x_gst_mop')
    diff = fields.Float(string='Diff', digits='Product Price', compute='_compute_diff')
    margin = fields.Float(string='Margin', digits=(12, 2), compute='_compute_margin')
    total = fields.Float(string='Total', digits='Product Price', compute='_compute_total')

    report_id = fields.Many2one(
        'ad.margin.report.header',
        string='Report',
        ondelete='cascade',
        required=True,
        index=True,
        tracking=True,
    )
    invoice_date = fields.Date(string='Invoice Date', related='invoice_id.invoice_date', store=True, readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)

    def write(self, vals):
        res = super().write(vals)
        if vals and res:
            labels = [self._fields[k].string for k in vals if k in self._fields and k != 'report_id']
            if labels:
                for line in self:
                    if line.report_id:
                        line.report_id.message_post(
                            body=_('AD Margin line updated (%s): %s') % (
                                line.item_name or line.product_id.name, ', '.join(labels)
                            ),
                            message_type='notification',
                        )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line in lines:
            if line.report_id:
                line.report_id.message_post(
                    body=_('AD Margin line added: %s') % (line.item_name or line.product_id.name),
                    message_type='notification',
                )
        return lines

    def unlink(self):
        headers = self.report_id
        res = super().unlink()
        for header in headers:
            if header.exists():
                header.message_post(
                    body=_('AD Margin line(s) removed'),
                    message_type='notification',
                )
        return res

    @api.depends('mop')
    def _compute_x_gst_mop(self):
        """Calculate X GST MO = MOP / (1 + GST_rate)"""
        company = self.env.company
        gst_rate = 0.18
        if hasattr(company, 'gst_rate') and company.gst_rate:
            gst_rate = company.gst_rate / 100.0
        for record in self:
            if record.mop:
                record.x_gst_mop = record.mop / (1 + gst_rate)
            else:
                record.x_gst_mop = 0.0

    @api.depends('sales_rate', 'x_gst_mop')
    def _compute_diff(self):
        for record in self:
            record.diff = record.sales_rate - record.x_gst_mop

    @api.depends('diff', 'x_gst_mop')
    def _compute_margin(self):
        for record in self:
            if record.x_gst_mop and record.x_gst_mop != 0:
                record.margin = (record.diff / record.x_gst_mop) * 100
            else:
                record.margin = 0.0

    @api.depends('diff', 'sales_quantity')
    def _compute_total(self):
        for record in self:
            record.total = record.diff * record.sales_quantity


class AdMarginReportWizard(models.TransientModel):
    _name = 'ad.margin.report.wizard'
    _description = 'AD Margin Report Wizard'

    name = fields.Char(string='Report Name', default='AD Margin Report')
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

    partner_ids = fields.Many2many('res.partner', string='Customers', domain=[('is_company', '=', True)])
    product_ids = fields.Many2many('product.product', string='Products')
    brand_id = fields.Many2one('product.brand', string='Brand')
    category_id = fields.Many2one('product.category', string='Category')

    def action_generate_report(self):
        self.ensure_one()

        domain = [
            ('move_id.move_type', '=', 'out_invoice'),
            ('move_id.state', '=', 'posted'),
            ('move_id.invoice_date', '>=', self.date_from),
            ('move_id.invoice_date', '<=', self.date_to),
            ('product_id', '!=', False),
        ]

        if self.partner_ids:
            domain.append(('move_id.partner_id', 'in', self.partner_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.brand_id:
            domain.append(('product_id.brand_id', '=', self.brand_id.id))
        if self.category_id:
            domain.append(('product_id.categ_id', 'child_of', self.category_id.id))

        invoice_lines = self.env['account.move.line'].search(domain)

        if not invoice_lines:
            raise UserError(_('No invoice lines found for the selected criteria.'))

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

            qty = line.quantity
            price = line.price_unit
            report_data[key]['sales_quantity'] += qty
            report_data[key]['total_amount'] += qty * price

        report_lines = []
        for (partner_id, product_id), data in report_data.items():
            product = self.env['product.product'].browse(product_id)

            if data['sales_quantity'] > 0:
                avg_sales_rate = data['total_amount'] / data['sales_quantity']
            else:
                avg_sales_rate = 0.0

            # MOP from MOP Master only (by report date_to, same as Funnel)
            mop_date = self.date_to or fields.Date.today()
            mop = self.env['mop.master'].get_current_mop(product_id, mop_date)
            if mop is False:
                mop = 0.0

            report_lines.append({
                'partner_id': partner_id,
                'product_id': product_id,
                'sales_rate': avg_sales_rate,
                'sales_quantity': data['sales_quantity'],
                'mop': mop,
                'invoice_id': data['invoice_id'],
            })

        header = self.env['ad.margin.report.header'].create({
            'name': self.name or 'AD Margin Report',
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        for vals in report_lines:
            vals['report_id'] = header.id
            self.env['ad.margin.report'].create(vals)

        return {
            'name': _('AD Margin Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'ad.margin.report.header',
            'res_id': header.id,
            'view_mode': 'form',
            'target': 'current',
        }
