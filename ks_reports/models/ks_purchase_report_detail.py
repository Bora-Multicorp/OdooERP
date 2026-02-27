# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools import html2plaintext


class KsPurchaseReportDetail(models.Model):
    _name = 'ks.purchase.report.detail'
    _description = 'Purchase Report Detail (synced from PO)'
    _order = 'purchase_id, id'

    purchase_line_id = fields.Many2one(
        'purchase.order.line',
        string='PO Line',
        ondelete='cascade',
        index=True,
        help='Used to match and update records on sync (one record per PO line).'
    )
    purchase_id = fields.Many2one(
        'purchase.order',
        string='PO Number',
        required=True,
        ondelete='cascade',
        index=True
    )
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Bill or Advance',
        related='purchase_id.payment_term_id',
        store=True,
        readonly=True
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice No',
        ondelete='set null',
        help='First linked bill from the PO.'
    )
    invoice_date = fields.Date(
        string='Invoice Date',
        compute='_compute_invoice_date',
        store=True,
        readonly=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Purchase Manager',
        related='purchase_id.user_id',
        store=True,
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='INWARD IN',
        related='purchase_id.company_id',
        store=True,
        readonly=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor Name',
        related='purchase_id.partner_id',
        store=True,
        readonly=True
    )
    vendor_gstin = fields.Char(string='Vendor GSTIN', default='Test')
    product_id = fields.Many2one(
        'product.product',
        string='Model',
        ondelete='set null'
    )
    po_qty = fields.Float(string='PO Qty', digits='Product Unit of Measure')
    grn_qty = fields.Float(string='GRN Qty', digits='Product Unit of Measure', default=0.0)
    difference = fields.Float(
        string='Difference',
        compute='_compute_difference',
        store=True,
        digits='Product Unit of Measure',
        readonly=True
    )
    rate = fields.Float(string='Rate', digits='Product Price')
    amt = fields.Float(
        string='Amount',
        compute='_compute_amt',
        store=True,
        digits='Product Price',
        readonly=True
    )
    remarks = fields.Text(string='Remarks')
    # Extra PO fields (mapped directly from PO Other Info → Extra PO Field)
    ks_invoice = fields.Char(string='Invoice')
    ks_e_invoices = fields.Char(string='E - Invoices')
    ks_e_way_bill = fields.Char(string='E-way Bill')
    ks_imei_serial_no = fields.Char(string='IMEI/ Serial No')
    ks_docket = fields.Char(string='DOCKET')
    ks_ewaybill_no = fields.Char(string='EWAYBILL NO')
    ks_docket_no = fields.Char(string='DOCKET No')
    ks_transporter = fields.Char(string='TRANSPORTER')
    ks_vehicle_no = fields.Char(string='Vehicle No.')
    ks_remarks_po = fields.Char(string='Remarks (PO)')

    @api.depends('invoice_id', 'invoice_id.invoice_date')
    def _compute_invoice_date(self):
        for r in self:
            r.invoice_date = r.invoice_id.invoice_date if r.invoice_id else False

    @api.depends('po_qty', 'grn_qty')
    def _compute_difference(self):
        for r in self:
            r.difference = r.po_qty - r.grn_qty

    @api.depends('po_qty', 'rate')
    def _compute_amt(self):
        for r in self:
            r.amt = r.po_qty * r.rate

    @api.model
    def action_sync_po_data(self, purchase_orders=None):
        """
        Create/update ks.purchase.report.detail from purchase orders.
        When called from cron, purchase_orders is None and all POs are synced.
        When called from PO form button, only the given PO(s) are synced.
        Uniqueness: one record per PO line (matched by purchase_line_id).
        """
        if purchase_orders is None:
            purchase_orders = self.env['purchase.order'].search([])
        if not purchase_orders:
            return True

        ReportDetail = self.env['ks.purchase.report.detail']
        for order in purchase_orders:
            # First linked bill (for invoice_id / invoice_date)
            first_invoice = order.invoice_ids.filtered(
                lambda m: m.state not in ('cancel', 'draft')
            )[:1]
            invoice_id = first_invoice.id if first_invoice else False
            remarks_text = html2plaintext(order.notes).strip() or '' if order.notes else ''

            # Product lines only (skip sections and notes)
            lines = order.order_line.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note')
            )
            line_ids = lines.ids
            # One search per order: existing report details by purchase_line_id
            existing_by_line = {
                r.purchase_line_id.id: r
                for r in ReportDetail.search([
                    ('purchase_id', '=', order.id),
                    ('purchase_line_id', 'in', line_ids),
                ])
            }
            # Fallback: records with same PO + product but no line (legacy)
            existing_no_line = ReportDetail.search([
                ('purchase_id', '=', order.id),
                ('purchase_line_id', '=', False),
            ])
            by_product = {r.product_id.id: r for r in existing_no_line}

            for line in lines:
                existing = existing_by_line.get(line.id)
                if not existing and line.product_id:
                    existing = by_product.pop(line.product_id.id, None)
                product_id = line.product_id.id if line.product_id else False
                vals = {
                    'purchase_line_id': line.id,
                    'purchase_id': order.id,
                    'invoice_id': invoice_id,
                    'product_id': product_id,
                    'po_qty': line.product_qty,
                    'grn_qty': line.qty_received,
                    'rate': line.price_unit,
                    'remarks': remarks_text,
                    'ks_invoice': getattr(order, 'ks_invoice', None) or '',
                    'ks_e_invoices': getattr(order, 'ks_e_invoices', None) or '',
                    'ks_e_way_bill': getattr(order, 'ks_e_way_bill', None) or '',
                    'ks_imei_serial_no': getattr(order, 'ks_imei_serial_no', None) or '',
                    'ks_docket': getattr(order, 'ks_docket', None) or '',
                    'ks_ewaybill_no': getattr(order, 'ks_ewaybill_no', None) or '',
                    'ks_docket_no': getattr(order, 'ks_docket_no', None) or '',
                    'ks_transporter': getattr(order, 'ks_transporter', None) or '',
                    'ks_vehicle_no': getattr(order, 'ks_vehicle_no', None) or '',
                    'ks_remarks_po': getattr(order, 'ks_remarks', None) or '',
                }
                if existing:
                    existing.write(vals)
                else:
                    ReportDetail.create(vals)

            # Remove report details for PO lines that were removed from the order
            if line_ids:
                ReportDetail.search([
                    ('purchase_id', '=', order.id),
                    ('purchase_line_id', '!=', False),
                    ('purchase_line_id', 'not in', line_ids),
                ]).unlink()
            else:
                ReportDetail.search([
                    ('purchase_id', '=', order.id),
                    ('purchase_line_id', '!=', False),
                ]).unlink()

        return True
