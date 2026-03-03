# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ===== Advance Payment Fields =====
    ks_advance_payment_ids = fields.One2many(
        comodel_name='account.payment',
        inverse_name='ks_sale_order_id',
        string='Advance Payments',
        copy=False,
        help='Advance payments linked to this Sale Order',
    )
    ks_advance_payment_count = fields.Integer(
        string='Advance Payment Count',
        compute='_compute_ks_advance_payment_count',
    )
    ks_advance_payment_amount = fields.Monetary(
        string='Advance Payment Amount',
        compute='_compute_ks_advance_payment_amount',
        currency_field='currency_id',
        store=True,
        help='Total amount of advance payments received for this Sale Order',
    )
    total_payment_received = fields.Integer()
    ks_advance_payment_balance = fields.Monetary(
        string='Balance Due',
        compute='_compute_ks_advance_payment_amount',
        currency_field='currency_id',
        store=True,
        help='Remaining balance after advance payments',
    )


    total_invoice_payment_received = fields.Monetary(
        string="Total Invoice Payment Received",
        compute="_compute_total_payment_received",
        store=True,  # Store=True zaroori hai agar aapko reports ya search mein use karna hai
        currency_field='currency_id'
    )

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.reconciled_payment_ids',
                 'invoice_ids.reconciled_payment_ids.state', 'invoice_ids.reconciled_payment_ids.amount')
    def _compute_total_payment_received(self):
        for order in self:
            total = 0.0

            # 1. Retrieve all Posted Invoices and Credit Notes linked to the Sale Order
            invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')

            for inv in invoices:
                # 2. Sum the amounts of payment records that are in 'posted' (paid) state
                # We filter the recordset before mapping the amount
                valid_payments = inv.reconciled_payment_ids.filtered(lambda p: p.state == 'posted')
                invoice_payment_sum = sum(valid_payments.mapped('amount'))

                # 3. Add to total if it's a standard Invoice, subtract if it's a Credit Note
                if inv.move_type == 'out_invoice':
                    total += invoice_payment_sum
                elif inv.move_type == 'out_refund':
                    total -= invoice_payment_sum

            # Update the field with the final calculated sum
            order.total_invoice_payment_received = total

    @api.depends('ks_advance_payment_ids')
    def _compute_ks_advance_payment_count(self):
        """Compute the number of advance payments linked to this SO"""
        for order in self:
            order.ks_advance_payment_count = len(order.ks_advance_payment_ids)

    @api.depends(
        'ks_advance_payment_ids',
        'ks_advance_payment_ids.amount',
        'ks_advance_payment_ids.state',
        'ks_advance_payment_ids.currency_id',
        'amount_total',
    )
    def _compute_ks_advance_payment_amount(self):
        """Compute the total advance payment amount received (paid/in_process payments only)."""
        # Odoo 18 account.payment uses 'paid' and 'in_process', not 'posted'
        for order in self:
            payments = self.env['account.payment'].search([
                ('ks_sale_order_id', '=', order.id),
                ('state', '=', 'paid'),
            ])
            total_advance = sum(payments.mapped('amount')) if payments else 0.0
            order.ks_advance_payment_amount = total_advance
            order.ks_advance_payment_balance = (order.amount_total or 0.0) - total_advance

    def action_create_advance_payment(self):
        """Open wizard to create advance payment directly"""
        self.ensure_one()
        return {
            'name': _('Create Advance Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.advance.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
            }
        }

    def action_view_advance_payments(self):
        """View all advance payments linked to this Sale Order"""
        self.ensure_one()
        action = {
            'name': _('Advance Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        
        if self.ks_advance_payment_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.ks_advance_payment_ids.id
        else:
            action['view_mode'] = 'list,form'
            action['domain'] = [('id', 'in', self.ks_advance_payment_ids.ids)]
        
        return action

