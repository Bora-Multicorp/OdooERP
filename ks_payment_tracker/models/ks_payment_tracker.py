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
    # Payment approval type: with bill vs without bill (for report/workflow)
    payment_approval_type = fields.Selection(
        [
            ('with_bill', 'Payment approval with bill for purchase'),
            ('without_bill', 'Payment approval without bill for purchase'),
        ],
        string='Payment Approval Type',
        required=True,
        default='with_bill',
        help='Whether this payment approval is with or without vendor bill.',
    )
    # Approval workflow state
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending_approval', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        default='draft',
        required=True,
        help='Approval workflow state.',
    )
    approved = fields.Boolean(
        string='Approved',
        default=False,
        compute='_compute_approved',
        store=True,
        help='True when state is approved (kept for backward compatibility).',
    )
    approved_notes = fields.Text(string='Approved Notes')
    approval_user_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
    )
    approval_date = fields.Datetime(string='Approval Date', readonly=True, copy=False)
    rejection_notes = fields.Text(string='Rejection Notes', readonly=True, copy=False)

    currency_id = fields.Many2one(
        'res.currency',
        related='purchase_order_id.currency_id',
        store=True,
        readonly=True,
    )

    @api.depends('state')
    def _compute_approved(self):
        for rec in self:
            rec.approved = rec.state == 'approved'

    def _get_next_sn(self):
        last = self.search([], order='sn desc', limit=1)
        return (last.sn or 0) + 1

    def action_submit_for_approval(self):
        """Move to Pending Approval."""
        self.check_can_submit()
        self.write({'state': 'pending_approval'})
        return True

    def check_can_submit(self):
        if any(r.state != 'draft' for r in self):
            raise UserError(_('Only draft records can be submitted for approval.'))

    def action_approve(self):
        """Approve payment tracker line(s)."""
        for rec in self:
            if rec.state != 'pending_approval':
                raise UserError(_('Only pending records can be approved.'))
        self.write({
            'state': 'approved',
            'approval_user_id': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })
        return True

    def action_reject(self):
        """Reject payment tracker line(s). Opens wizard or uses context rejection_notes."""
        for rec in self:
            if rec.state != 'pending_approval':
                raise UserError(_('Only pending records can be rejected.'))
        notes = self.env.context.get('rejection_notes', '')
        self.write({
            'state': 'rejected',
            'rejection_notes': notes,
        })
        return True

    def action_reset_to_draft(self):
        """Reset to draft (e.g. for correction)."""
        self.write({
            'state': 'draft',
            'approval_user_id': False,
            'approval_date': False,
            'rejection_notes': False,
        })
        return True

    @api.model_create_multi
    def create(self, vals_list):
        next_sn = self._get_next_sn()
        for vals in vals_list:
            if not vals.get('sn'):
                vals['sn'] = next_sn
                next_sn += 1
        return super().create(vals_list)
