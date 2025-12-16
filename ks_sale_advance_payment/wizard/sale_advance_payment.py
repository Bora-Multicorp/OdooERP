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
    amount = fields.Monetary(
        string='Payment Amount',
        required=True,
        currency_field='currency_id',
        help="The amount to be paid in advance."
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        compute='_compute_currency_id',
        store=True,
        readonly=True
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

    @api.depends('sale_order_id')
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = wizard.sale_order_id.currency_id

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

    def action_create_payment(self):
        """Create account.payment record directly from sale order"""
        self.ensure_one()
        
        if not self.amount or self.amount <= 0:
            raise UserError(_('The payment amount must be positive.'))
        
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
        
        # Prepare payment values
        payment_vals = {
            'amount': self.amount,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': accounting_partner.id,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'date': self.payment_date,
            'destination_account_id': destination_account.id,
            'memo': self.memo or _('Advance payment for %s', self.sale_order_id.name),
        }
        
        # Create the payment
        payment = self.env['account.payment'].create(payment_vals)
        
        # Post the payment
        payment.action_post()
        
        # Link payment to sale order (optional - you can add a many2many field on sale.order if needed)
        # For now, we'll just add a message on the sale order
        formatted_amount = formatLang(self.env, self.amount, currency_obj=self.currency_id)
        self.sale_order_id.message_post(
            body=_('Advance payment %s of %s has been created and posted.', 
                   payment.name, 
                   formatted_amount)
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

