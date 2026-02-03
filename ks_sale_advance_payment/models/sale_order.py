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
        help='Total amount of advance payments received for this Sale Order',
    )
    ks_advance_payment_balance = fields.Monetary(
        string='Balance Due',
        compute='_compute_ks_advance_payment_amount',
        currency_field='currency_id',
        help='Remaining balance after advance payments',
    )

    @api.depends('ks_advance_payment_ids')
    def _compute_ks_advance_payment_count(self):
        """Compute the number of advance payments linked to this SO"""
        for order in self:
            order.ks_advance_payment_count = len(order.ks_advance_payment_ids)

    @api.depends('ks_advance_payment_ids', 'ks_advance_payment_ids.amount', 
                 'ks_advance_payment_ids.state', 'amount_total')
    def _compute_ks_advance_payment_amount(self):
        """Compute the total advance payment amount received"""
        for order in self:
            # Only count posted payments
            posted_payments = order.ks_advance_payment_ids.filtered(
                lambda p: p.state == 'posted'
            )
            total_advance = sum(posted_payments.mapped('amount'))
            order.ks_advance_payment_amount = total_advance
            order.ks_advance_payment_balance = order.amount_total - total_advance

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

