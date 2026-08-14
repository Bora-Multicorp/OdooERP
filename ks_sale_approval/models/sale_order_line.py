# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Computed field to check if current user can edit price
    ks_can_edit_price = fields.Boolean(
        string='Can Edit Price',
        compute='_compute_ks_can_edit_price',
        store=False,
        default=False,
    )
    # Minimum allowed unit price (in order currency) from latest purchase price - for display
    ks_min_unit_price = fields.Monetary(
        string='Min. Unit Price (from Purchase)',
        currency_field='currency_id',
        compute='_compute_ks_min_unit_price',
        store=False,
        help='Minimum unit price allowed: latest purchase price converted to order currency.',
    )

    @api.depends('product_id', 'order_id.currency_id', 'order_id.company_id', 'order_id.date_order')
    def _compute_ks_min_unit_price(self):
        """
        Minimum allowed unit price in SO currency.
        Converts product's latest purchase price (e.g. INR) to order currency (e.g. USD) for display.
        """
        for line in self:
            order = line.order_id
            if not line.product_id or not order or not order.company_id or not order.currency_id:
                line.ks_min_unit_price = 0.0
                continue
            company = order.company_id
            product = line.product_id.with_company(company)
            if not product.ks_latest_purchase_currency_id:
                line.ks_min_unit_price = 0.0
                continue
            from_cur = product.ks_latest_purchase_currency_id
            to_cur = order.currency_id
            date = order.date_order.date() if order.date_order else fields.Date.today()
            amount = product.ks_latest_purchase_price
            if from_cur == to_cur:
                line.ks_min_unit_price = amount
                continue
            try:
                if order.is_exchange and order.rate:
                    line.ks_min_unit_price = amount / order.rate
                else:
                    line.ks_min_unit_price = from_cur._convert(
                        amount,
                        to_cur,
                        company=company,
                        date=date,
                        round=False,
                    )
            except Exception:
                line.ks_min_unit_price = 0.0

    @api.depends_context('uid')
    @api.depends('order_id.state', 'order_id.ks_edit_approved', 'order_id.ks_edit_request_user_id')
    def _compute_ks_can_edit_price(self):
        """
        Check if current user can edit the price.
        - In draft/sent: all users can edit unit price
        - Admin users can always edit prices (bypass all restrictions)
        - PM users can always edit prices
        - Normal users can edit prices if edit request was approved for them
        """
        for line in self:
            # Draft (and sent): unit price editable for all users
            if line.order_id and line.order_id.state in ('draft', 'sent'):
                line.ks_can_edit_price = True
                continue
            # Admin users can always edit prices - bypass all restrictions
            if line.order_id and line.order_id._is_admin_user():
                line.ks_can_edit_price = True
                continue
            
            if line.order_id and line.order_id._has_approval_config():
                config = line.order_id._get_approval_config()
                all_pms = config.get_all_pm_users()
                is_pm = self.env.user in all_pms
                
                # PM users can always edit
                if is_pm:
                    line.ks_can_edit_price = True
                else:
                    # Normal user - check if edit was approved for them
                    order = line.order_id
                    if order.ks_edit_approved and order.ks_edit_request_user_id == self.env.user:
                        # Edit was approved for this user - allow price editing
                        line.ks_can_edit_price = True
                    else:
                        line.ks_can_edit_price = False
            else:
                # No config - allow price editing (standard behavior)
                line.ks_can_edit_price = True

    @api.model
    def create(self, vals):
        """Override create to check price permissions
        
        Admin users can always set custom prices (bypass all restrictions).
        """
        line = super().create(vals)
        
        # Admin users can always set custom prices - bypass all restrictions
        if line.order_id and line.order_id._is_admin_user():
            return line

        # Advance payment deduction lines are managed by the system — always allow
        if line.product_id and line.product_id.product_tmpl_id.is_advance_payment_product:
            return line

        # In draft/sent, all users can set unit price
        if line.order_id and line.order_id.state in ('draft', 'sent'):
            return line

        # Check if user tried to set a custom price and is not a PM
        if line.order_id and line.order_id._has_approval_config():
            config = line.order_id._get_approval_config()
            all_pms = config.get_all_pm_users()
            
            if self.env.user not in all_pms:
                # Normal user - check if edit was approved for them
                order = line.order_id
                edit_approved_for_user = (
                    order.ks_edit_approved and 
                    order.ks_edit_request_user_id == self.env.user
                )
                
                if not edit_approved_for_user:
                    # Edit not approved - check if price_unit was manually set
                    if 'price_unit' in vals:
                        # Get the product's expected price
                        expected_price = line._get_expected_price()
                        if expected_price is not None:
                            # Allow small tolerance for rounding
                            currency = line.currency_id or line.company_id.currency_id or self.env.company.currency_id
                            if currency.compare_amounts(vals.get('price_unit', 0), expected_price) != 0:
                                raise UserError(_(
                                    "You do not have permission to change item prices. "
                                    "Please contact a PM user to modify prices."
                                ))
        
        return line

    def write(self, values):
        """Override write to prevent normal users from changing prices, discounts, or taxes

        Admin users can always edit (bypass all restrictions).
        """
        # Block normal users from changing tax_id on confirmed/locked orders
        if 'tax_id' in values:
            for line in self:
                if not line.order_id or not line.order_id.locked:
                    continue
                if line.order_id._is_admin_user():
                    continue
                if not line.order_id._has_approval_config():
                    continue
                config = line.order_id._get_approval_config()
                if self.env.user in config.get_all_pm_users():
                    continue
                edit_approved = (
                    line.order_id.ks_edit_approved and
                    line.order_id.ks_edit_request_user_id == self.env.user
                )
                if not edit_approved:
                    raise UserError(_(
                        "You do not have permission to change taxes on order lines. "
                        "Please use 'Request Edit' to get edit approval first."
                    ))

        # Check if price_unit or discount is being changed
        price_fields = ['price_unit', 'discount']
        changing_price = any(field in values for field in price_fields)

        if changing_price:
            for line in self:
                # Admin users can always edit prices - bypass all restrictions
                if line.order_id and line.order_id._is_admin_user():
                    continue
                # Advance payment deduction lines are managed by the system — always allow
                if line.product_id and line.product_id.product_tmpl_id.is_advance_payment_product:
                    continue
                # In draft/sent, all users can edit unit price
                if line.order_id and line.order_id.state in ('draft', 'sent'):
                    continue
                if line.order_id and line.order_id._has_approval_config():
                    config = line.order_id._get_approval_config()
                    all_pms = config.get_all_pm_users()
                    
                    if self.env.user not in all_pms:
                        # Normal user - check if edit was approved for them
                        order = line.order_id
                        edit_approved_for_user = (
                            order.ks_edit_approved and 
                            order.ks_edit_request_user_id == self.env.user
                        )
                        
                        if not edit_approved_for_user:
                            # Edit not approved - block price/discount changes
                            # Allow if it's from a compute (product change, etc.)
                            if not self.env.context.get('sale_write_from_compute'):
                                # Check if price is actually different
                                if 'price_unit' in values:
                                    currency = line.currency_id or line.company_id.currency_id or self.env.company.currency_id
                                    if currency.compare_amounts(values.get('price_unit', 0), line.price_unit) != 0:
                                        raise UserError(_(
                                            "You do not have permission to change item prices. "
                                            "Please contact a PM user to modify prices."
                                        ))
                                # Check if discount is actually different
                                if 'discount' in values:
                                    if values.get('discount', 0) != line.discount:
                                        raise UserError(_(
                                            "You do not have permission to change item discounts. "
                                            "Please contact a PM user to modify discounts."
                                        ))
        
        return super().write(values)

    def _get_expected_price(self):
        """Get the expected price from product/pricelist"""
        self.ensure_one()
        if not self.product_id:
            return None
        
        line = self.with_company(self.company_id)
        price = line._get_display_price()
        product_taxes = line.product_id.taxes_id._filter_taxes_by_company(line.company_id)
        price_unit = line.product_id._get_tax_included_unit_price_from_price(
            price,
            product_taxes=product_taxes,
            fiscal_position=line.order_id.fiscal_position_id,
        )
        return price_unit

    def _ks_get_sale_price_in_order_currency(self):
        """
        Return line's price_unit in order currency.
        Sale line price is already in order.currency_id, so no conversion needed.
        """
        self.ensure_one()
        if not self.order_id or not self.product_id or self.display_type:
            return None
        if not self.order_id.currency_id:
            return None
        return self.price_unit

    def _ks_get_latest_purchase_price_in_order_currency(self):
        """
        Return product's latest purchase price converted to order's currency.
        Handles multi-currency: latest purchase in INR, SO in USD → converts INR to USD.
        """
        self.ensure_one()
        order = self.order_id
        if not self.product_id or not order or not order.currency_id or not order.company_id:
            return None
        company = order.company_id
        product = self.product_id.with_company(company)
        if not product.ks_latest_purchase_currency_id:
            return None
        from_cur = product.ks_latest_purchase_currency_id
        to_cur = order.currency_id
        date = order.date_order.date() if order.date_order else fields.Date.today()
        amount = product.ks_latest_purchase_price
        if from_cur == to_cur:
            return amount
        try:
            if order.is_exchange and order.rate:
                return amount / order.rate
            else:
                return from_cur._convert(
                    amount,
                    to_cur,
                    company=company,
                    date=date,
                    round=False,
                )
        except Exception:
            return None

    def _check_sale_price_not_below_latest_purchase(self):
        """
        Check if sales price is below latest purchase price.
        Warning dialog and approver checks are handled on sale.order level.
        """
        pass

