# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang


class SaleAdvancePayment(models.TransientModel):
    _name = 'sale.advance.payment'
    _description = "Sales Advance Payment (Direct Payment)"

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    order_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Order Currency',
        related='sale_order_id.currency_id',
        readonly=True,
    )
    payment_currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Payment Currency',
        required=True,
        help="Currency of the payment amount. Defaults to order currency.",
    )
    amount = fields.Monetary(
        string='Payment Amount',
        required=True,
        currency_field='payment_currency_id',
        help="Amount in the selected payment currency.",
    )
    use_manual_rate = fields.Boolean(
        string='Use Manual Rate',
        default=False,
        help="If set, use the manual rate below instead of the currency rate at payment date.",
    )
    manual_rate = fields.Float(
        string='Manual Rate (1 Payment = X Order)',
        digits=(16, 6),
        default=1.0,
        help="Rate: 1 unit of payment currency = X units of order currency.",
    )
    amount_in_order_currency = fields.Monetary(
        string='Amount in Order Currency',
        compute='_compute_amount_in_order_currency',
        currency_field='order_currency_id',
        readonly=True,
        help="Payment amount converted to the sale order currency.",
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        related='order_currency_id',
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        compute='_compute_company_id',
        store=True,
        readonly=True
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Payment Journal',
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]",
        help="The journal used to record the payment."
    )
    payment_method_line_id = fields.Many2one(
        comodel_name='account.payment.method.line',
        string='Payment Method',
        domain="[('id', 'in', available_payment_method_line_ids)]",
        help="The payment method used for this payment."
    )
    available_payment_method_line_ids = fields.Many2many(
        comodel_name='account.payment.method.line',
        compute='_compute_available_payment_method_line_ids'
    )
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today
    )
    memo = fields.Char(
        string='Memo',
        help="Internal note about this payment."
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        related='sale_order_id.partner_id',
        readonly=True
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'sale_order_id' in res and res['sale_order_id']:
            order = self.env['sale.order'].browse(res['sale_order_id'])
            if 'payment_currency_id' not in res or not res.get('payment_currency_id'):
                res['payment_currency_id'] = order.currency_id.id
            if 'manual_rate' not in res or not res.get('manual_rate'):
                res['manual_rate'] = 1.0
        return res

    @api.depends('payment_currency_id', 'order_currency_id', 'amount', 'use_manual_rate', 'manual_rate', 'payment_date', 'company_id')
    def _compute_amount_in_order_currency(self):
        for wizard in self:
            if not wizard.amount or not wizard.payment_currency_id or not wizard.order_currency_id:
                wizard.amount_in_order_currency = 0.0
                continue
            if wizard.payment_currency_id == wizard.order_currency_id:
                wizard.amount_in_order_currency = wizard.amount
            elif wizard.use_manual_rate and wizard.manual_rate:
                wizard.amount_in_order_currency = wizard.amount * wizard.manual_rate
            else:
                wizard.amount_in_order_currency = wizard.payment_currency_id._convert(
                    wizard.amount,
                    wizard.order_currency_id,
                    wizard.company_id,
                    wizard.payment_date or fields.Date.context_today(wizard),
                )

    @api.onchange('payment_currency_id', 'order_currency_id')
    def _onchange_payment_currency_id(self):
        if self.payment_currency_id and self.order_currency_id and self.payment_currency_id == self.order_currency_id:
            self.use_manual_rate = False
            self.manual_rate = 1.0
        elif self.payment_currency_id and self.order_currency_id and not self.use_manual_rate:
            try:
                self.manual_rate = self.env['res.currency']._get_conversion_rate(
                    self.payment_currency_id,
                    self.order_currency_id,
                    self.company_id,
                    self.payment_date or fields.Date.context_today(self),
                )
            except Exception:
                self.manual_rate = 1.0

    @api.depends('sale_order_id')
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.sale_order_id.company_id

    @api.depends('journal_id')
    def _compute_available_payment_method_line_ids(self):
        for wizard in self:
            if wizard.journal_id:
                wizard.available_payment_method_line_ids = wizard.journal_id.inbound_payment_method_line_ids
            else:
                wizard.available_payment_method_line_ids = False

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id and self.journal_id.inbound_payment_method_line_ids:
            self.payment_method_line_id = self.journal_id.inbound_payment_method_line_ids[0]

    def _add_advance_deduction_line(self):
        """Add a sale order line to reduce the SO total by the advance amount (e.g. SO 100, advance 20 → total 80)."""
        self.ensure_one()
        product = self.env.ref(
            'ks_sale_advance_payment.product_template_advance_deduction',
            raise_if_not_found=False
        )
        if not product:
            return
        product = product.product_variant_id
        if not product:
            return
        order = self.sale_order_id
        # Create line: Advance Payment Deduction, qty 1, unit price = -advance amount
        line_vals = {
            'order_id': order.id,
            'product_id': product.id,
            'name': _('Advance payment received'),
            'product_uom_qty': 1.0,
            'product_uom': product.uom_id.id,
            'price_unit': -self.amount_in_order_currency,
            'tax_id': [(5, 0, 0)],  # No tax on deduction
        }
        line = self.env['sale.order.line'].create(line_vals)
        # Ensure price is not overwritten by pricelist
        line.write({'price_unit': -self.amount_in_order_currency})

    def action_create_payment(self):
        """Create account.payment record directly from sale order"""
        self.ensure_one()
        
        if not self.amount or self.amount <= 0:
            raise UserError(_('The payment amount must be positive.'))
        if not self.amount_in_order_currency or self.amount_in_order_currency <= 0:
            raise UserError(_('The converted amount in order currency must be positive. Check the payment amount and rate.'))

        if not self.journal_id:
            raise UserError(_('Please select a payment journal.'))
        
        if not self.payment_method_line_id:
            raise UserError(_('Please select a payment method.'))
        
        # Get the partner's receivable account
        partner = self.sale_order_id.partner_id
        accounting_partner = self.env['res.partner']._find_accounting_partner(partner)
        destination_account = accounting_partner.with_company(self.company_id).property_account_receivable_id
        
        if not destination_account:
            raise UserError(_('No receivable account found for the customer. Please configure the customer account settings.'))
        
        # Prepare payment values with link to Sale Order (payment in order currency)
        payment_vals = {
            'amount': self.amount_in_order_currency,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': accounting_partner.id,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.order_currency_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'date': self.payment_date,
            'destination_account_id': destination_account.id,
            'memo': self.memo or _('Advance payment for %s', self.sale_order_id.name),
            # Link to Sale Order
            'ks_sale_order_id': self.sale_order_id.id,
        }
        
        # Create the payment
        payment = self.env['account.payment'].create(payment_vals)
        
        # Post the payment
        payment.action_post()
        
        # Update sale order: add a deduction line so SO total is reduced by advance amount (e.g. 100 - 20 = 80)
        self._add_advance_deduction_line()
        
        # Log in chatter
        formatted_amount = formatLang(self.env, self.amount_in_order_currency, currency_obj=self.order_currency_id)
        self.sale_order_id.message_post(
            body=_(
                'An advance payment has been created and posted. '
                'Payment: %s, '
                'Amount: %s',
                payment.name,
                formatted_amount
            )
        )
        
        # Return action to view the created payment
        return {
            'name': _('Payment Created'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': payment.id,
            'target': 'current',
        }

