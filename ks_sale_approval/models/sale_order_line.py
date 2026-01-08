# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Computed field to check if current user can edit price
    ks_can_edit_price = fields.Boolean(
        string='Can Edit Price',
        compute='_compute_ks_can_edit_price',
        store=False,
        default=False,
    )

    @api.depends_context('uid')
    @api.depends('order_id.ks_edit_approved', 'order_id.ks_edit_request_user_id')
    def _compute_ks_can_edit_price(self):
        """
        Check if current user can edit the price.
        - PM users can always edit prices
        - Normal users can edit prices if edit request was approved for them
        """
        for line in self:
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
        """Override create to check price permissions"""
        line = super().create(vals)
        
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
        """Override write to prevent normal users from changing prices or discounts"""
        # Check if price_unit or discount is being changed
        price_fields = ['price_unit', 'discount']
        changing_price = any(field in values for field in price_fields)
        
        if changing_price:
            for line in self:
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

