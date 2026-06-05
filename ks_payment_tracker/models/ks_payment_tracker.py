# -*- coding: utf-8 -*-
# Report source: report soruce/LO-002.xlsx
# Row 1 = description/behaviour, Row 3 = column names.
# One record per PO line; created when user selects POs and clicks "Submit for Payment Approval".

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class KsPaymentTracker(models.Model):
    _name = 'ks.payment.tracker'
    _description = 'Payment Tracker (LO-002 – list of open POs whose payment is pending)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sn, id'

    # ---- System generated ----
    sn = fields.Integer(string='SN', default=1, readonly=True, help='System generated serial number')
    company_id = fields.Many2one(
        'res.company',
        string='From',
        required=True,
        default=lambda self: self.env.company,
        help='Company name from which PO is generated',
    )

    # ---- Linked approval request ----
    payment_approval_request_id = fields.Many2one(
        'vendor.payment.approval.request',
        string='Payment Approval Request',
        ondelete='cascade',
        index=True,
    )

    # ---- Linked payment ----
    ks_account_payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        ondelete='set null',
        index=True,
        readonly=True,
        help='The actual payment record linked to this tracker entry',
    )

    ks_requested_amount = fields.Monetary(
        string='Requested Amount',
        related='payment_approval_request_id.amount_for_approval',
        store=True,
        readonly=True,
        currency_field='currency_id',
        help='Amount For Approval from the linked Payment Approval Request',
    )

    # ---- From PO ----
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='PO No',
        required=True,
        ondelete='cascade',
        index=True,
        help='Autofetched from PO',
    )
    purchase_line_id = fields.Many2one(
        'purchase.order.line',
        string='PO Line',
        ondelete='set null',
        index=True,
        help='Link to purchase order line',
    )
    user_id = fields.Many2one(
        'res.users',
        string='Sales Person',
        help='Autofetched (Purchase Manager / responsible user from PO)',
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        related='purchase_order_id.partner_id',
        store=True,
        readonly=True,
        help='Autofetched from PO',
    )

    # ---- Vendor bill / invoice ----
    invoice_no = fields.Char(
        string='Invoice No',
        help='Vendor bill no as received from vendor (text box)',
    )
    e_invoice = fields.Selection(
        [('applicable', 'Applicable'), ('not_applicable', 'Not Applicable')],
        string='E-Invoice',
        help='Dropdown: Applicable / Not Applicable',
    )

    # ---- Model / product (from PO lines) ----
    product_id = fields.Many2one(
        'product.product',
        string='Model',
        help='List of models from PO lines (one line per SKU)',
    )
    fa = fields.Selection(
        [('fresh', 'Fresh'), ('activated', 'Activated')],
        string='F/A',
        help='Dropdown: Fresh / Activated',
    )
    product_qty = fields.Float(
        string='Qty',
        digits='Product Unit of Measure',
        help='Total quantity of that model',
    )
    price_unit = fields.Float(
        string='Rate',
        digits='Product Price',
        help='Rate (incl GST)',
    )
    price_subtotal = fields.Float(
        string='Amount',
        digits='Product Price',
        help='Total amount (incl TDS)',
    )
    tds = fields.Float(
        string='TDS',
        digits='Account',
        help='TDS amount',
    )
    amt_to_be_paid = fields.Monetary(
        string='Amt To Be Paid',
        compute='_compute_amt_to_be_paid',
        store=False,
        currency_field='currency_id',
        help='Requested amount minus total paid amount for this PO',
    )

    # ---- Status / purpose ----
    stock_status = fields.Selection(
        [('received', 'Received'), ('not_received', 'Not Received')],
        string='Stock Status at transporter',
        help='To be updated manually: received / not received',
    )
    purpose = fields.Selection(
        [
            ('domestic', 'Domestic'),
            ('export', 'Export'),
            ('ecommerce', 'Ecommerce'),
        ],
        string='Purpose',
        help='Dropdown: Domestic, Export, Ecommerce',
    )
    purchase_date = fields.Date(
        string='Purchase Date',
        help='Order date from PO',
    )
    transporter_id = fields.Many2one(
        'res.partner',
        string='Transporter',
        domain=[('is_company', '=', True)],
        help='Dropdown with transporter master list',
    )
    at_warehouse = fields.Selection(
        [('received', 'Received'), ('not_received', 'Not Received')],
        string='At Warehouse',
        help='Mark as received after GRN',
    )
    # ---- Extra PO Fields ----
    ks_destination = fields.Char(string='Destination')
    ks_despatched_through = fields.Char(string='Despatched Through')
    ks_remarks = fields.Char(string='Remarks')
    ks_invoice = fields.Char(string='Invoice')
    ks_e_invoices = fields.Char(string='E-Invoices')
    ks_e_way_bill = fields.Char(string='E-way Bill')
    ks_imei_serial_no = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string='IMEI/Serial No',
        required=True,
        default='no',
    )
    ks_docket = fields.Char(string='Docket')
    ks_ewaybill_no = fields.Char(string='E-Way Bill No')
    ks_docket_no = fields.Char(string='Docket No')
    ks_vehicle_no = fields.Char(string='Vehicle No.')
    ks_transporter = fields.Char(string='Transporter')

    approved = fields.Boolean(
        string='Approved',
        default=False,
        help='Payment approval status',
    )
    approved_notes = fields.Text(string='Approved Notes')

    currency_id = fields.Many2one(
        'res.currency',
        related='purchase_order_id.currency_id',
        store=True,
        readonly=True,
    )

    ks_total_paid_amount = fields.Monetary(
        string='Total Paid Amount',
        compute='_compute_ks_total_paid_amount',
        currency_field='currency_id',
        help='Total amount paid (posted + paid payments) for this Purchase Order',
    )

    @api.depends('purchase_order_id')
    def _compute_ks_total_paid_amount(self):
        for rec in self:
            if not rec.purchase_order_id:
                rec.ks_total_paid_amount = 0.0
                continue
            payments = self.env['account.payment'].search([
                ('ks_purchase_order_id', '=', rec.purchase_order_id.id),
                ('state', 'in', ('posted', 'paid')),
                ('payment_type', '=', 'outbound'),
            ])
            rec.ks_total_paid_amount = sum(payments.mapped('amount'))

    @api.depends(
        'price_subtotal',
        'purchase_order_id',
        'purchase_order_id.ks_advance_payment_ids',
        'purchase_order_id.ks_advance_payment_ids.amount',
        'purchase_order_id.ks_advance_payment_ids.state',
    )
    def _compute_amt_to_be_paid(self):
        for rec in self:
            paid = 0.0
            if rec.purchase_order_id:
                payments = self.env['account.payment'].search([
                    ('ks_purchase_order_id', '=', rec.purchase_order_id.id),
                    ('state', 'in', ('posted', 'paid')),
                    ('payment_type', '=', 'outbound'),
                ])
                paid = sum(payments.mapped('amount'))
            rec.amt_to_be_paid = (rec.price_subtotal or 0.0) - paid

    def _get_next_sn(self):
        last = self.search([], order='sn desc', limit=1)
        return (last.sn or 0) + 1

    @api.model_create_multi
    def create(self, vals_list):
        next_sn = self._get_next_sn()
        for vals in vals_list:
            if not vals.get('sn'):
                vals['sn'] = next_sn
                next_sn += 1
        return super().create(vals_list)
