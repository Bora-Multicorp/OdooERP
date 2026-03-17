# -*- coding: utf-8 -*-
# Report source: report soruce/LO-002.xlsx
# Row 1 = description/behaviour, Row 3 = column names.
# One record per PO line; created when user selects POs and clicks "Submit for Payment Approval".

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class KsPaymentTracker(models.Model):
    _name = 'ks.payment.tracker'
    _description = 'Payment Tracker (LO-002 – list of open POs whose payment is pending)'
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
    amt_to_be_paid = fields.Float(
        string='Amt To Be Paid',
        digits='Account',
        help='Calculations as per formula or from PO lines',
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
