# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from .common import KsSaleApprovalCommon


class TestKsSaleApprovalPriceWarning(KsSaleApprovalCommon):
    """Test cases for Sale Unit Price below Purchase Price Warning functionality"""

    def test_01_price_below_purchase_warning_flag(self):
        """Test: Sale line price below purchase price sets warning flag without throwing ValidationError"""
        # Set latest purchase price on test product
        self.product.write({
            'ks_latest_purchase_price': 100.0,
            'ks_latest_purchase_currency_id': self.company.currency_id.id,
        })

        # Create SO with unit price 80.0 (below latest purchase price 100.0)
        order = self._create_sale_order(user=self.normal_user)
        order.order_line[0].write({'price_unit': 80.0})

        # Ensure line and order flag low price warning without blocking
        line = order.order_line[0]
        line._compute_ks_is_price_below_purchase()
        order._compute_ks_has_price_below_purchase()

        self.assertTrue(line.ks_is_price_below_purchase, "Line should flag price below purchase")
        self.assertTrue(order.ks_has_price_below_purchase, "Order should flag low price warning")
        self.assertIn("Sale Price 80.0", order.ks_price_below_purchase_warning_text)

    def test_02_can_process_order_with_low_price_warning(self):
        """Test: Normal user can submit and PM can confirm order even when low price warning is active"""
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        self.product.write({
            'ks_latest_purchase_price': 150.0,
            'ks_latest_purchase_currency_id': self.company.currency_id.id,
        })

        order = self._create_sale_order(user=self.normal_user)
        order.order_line[0].write({'price_unit': 100.0})

        # Normal user submits approval request
        order.with_user(self.normal_user)._ks_send_to_approval_pending()
        self.assertEqual(order.state, 'approval_pending')

        # PM approves confirmation
        order.with_user(self.pm1_user_1)._ks_do_approve_confirmation_with_reason("Approved despite low price", self.pm1_user_1)
        self.assertEqual(order.state, 'sale', "Order should move to sale state successfully")
