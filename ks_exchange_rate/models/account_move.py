# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    """Extend account.move to add exchanged amount calculation based on exchange rate"""
    _inherit = 'account.move'

    exchanged_amount = fields.Monetary(
        string='Exchanged Currency Amount',
        compute='_compute_exchanged_amount',
        store=True,
        currency_field='company_currency_id',
        help='Calculated as: Total Amount × Exchange Rate. '
             'Example: If total is 200 USD and rate is 50 (1 USD = 50 INR), then exchanged currency amount = 200 × 50 = 10,000 INR',
    )

    @api.depends('amount_total', 'rate', 'currency_id', 'company_currency_id', 'is_exchange', 'invoice_line_ids.price_subtotal')
    def _compute_exchanged_amount(self):
        """Calculate exchanged amount based on total amount and exchange rate
        
        Formula: exchanged_amount = amount_total / rate
        Example: If invoice total is 200 USD and rate is 50, then exchanged_amount = 200 / 50 = 4
        """
        for move in self:
            exchanged_amount = 0.0
            # Only calculate if currencies are different and exchange is enabled
            if (move.is_exchange and 
                move.currency_id != move.company_currency_id and 
                move.rate and move.rate > 0 and
                move.amount_total):
                # Calculate: document_total / exchange_rate
                # Example: 200 USD / 50 = 4
                exchanged_amount = move.amount_total * move.rate
            move.exchanged_amount = exchanged_amount


class AccountMoveLine(models.Model):
    """Extend account.move.line to add exchanged currency amount calculation based on exchange rate"""
    _inherit = 'account.move.line'

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='move_id.company_id.currency_id',
        readonly=True,
        store=True,
        help='Company Currency for exchanged amount calculation'
    )

    exchanged_amount = fields.Monetary(
        string='Exchanged Currency Amount',
        compute='_compute_exchanged_amount',
        store=True,
        currency_field='company_currency_id',
        help='Calculated as: Line Total / Exchange Rate. '
             'Example: If line total is 100 USD and rate is 50, then exchanged currency amount = 100 / 50 = 2',
    )

    @api.depends('price_subtotal', 'price_unit', 'quantity', 'discount', 'move_id.rate', 'move_id.currency_id', 'move_id.company_currency_id', 'move_id.is_exchange')
    def _compute_exchanged_amount(self):
        """Calculate exchanged currency amount for each line based on line total and exchange rate"""
        for line in self:
            exchanged_amount = 0.0
            if not line.move_id:
                line.exchanged_amount = exchanged_amount
                continue
                
            move = line.move_id
            # Check if exchange is enabled and currencies are different
            if not move.is_exchange:
                line.exchanged_amount = exchanged_amount
                continue
                
            if not move.currency_id or not move.company_currency_id:
                line.exchanged_amount = exchanged_amount
                continue
                
            if move.currency_id.id == move.company_currency_id.id:
                line.exchanged_amount = exchanged_amount
                continue
                
            if not move.rate or move.rate <= 0:
                line.exchanged_amount = exchanged_amount
                continue
            
            # Get line total - use price_subtotal (which is typically the Amount shown in the UI)
            # price_subtotal is in the move's currency and represents the line amount before tax
            line_total = line.price_subtotal or 0.0
            
            # If price_subtotal is 0 or not available, try price_total (tax included)
            if not line_total or line_total == 0:
                line_total = line.price_total or 0.0
            
            # If still 0, calculate from price_unit * quantity * (1 - discount/100)
            if not line_total or line_total == 0:
                discount_factor = 1 - (line.discount or 0.0) / 100.0
                line_total = (line.price_unit or 0.0) * (line.quantity or 0.0) * discount_factor
            
            # Calculate exchanged amount: line_total / exchange_rate
            # Example: 200 USD / 100 = 2 (in company currency)
            if line_total and line_total != 0:
                exchanged_amount = abs(line_total) * move.rate
            
            line.exchanged_amount = exchanged_amount

