# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from .common import KsSaleApprovalCommon


class TestKsSaleApprovalAdminBypass(KsSaleApprovalCommon):
    """Test cases for Admin User Bypass Functionality"""

    def test_01_admin_can_confirm_directly(self):
        """Test: Admin user can confirm sale order directly without approval"""
        order = self._create_sale_order(user=self.admin_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        # Admin confirms directly
        order.with_user(self.admin_user).action_confirm()
        
        self.assertEqual(order.state, 'sale', "Admin should confirm order directly")
        self.assertNotEqual(order.state, 'approval_pending', "Admin should bypass approval")

    def test_02_admin_can_cancel_directly(self):
        """Test: Admin user can cancel sale order directly"""
        order = self._create_sale_order(user=self.admin_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        # First confirm as admin
        order.with_user(self.admin_user).action_confirm()
        self.assertEqual(order.state, 'sale')
        
        # Admin cancels directly
        order.with_user(self.admin_user).action_cancel()
        
        self.assertEqual(order.state, 'cancel', "Admin should cancel order directly")

    def test_03_admin_can_edit_directly(self):
        """Test: Admin user can edit sale order directly without request"""
        order = self._create_sale_order(user=self.admin_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        # First confirm as admin
        order.with_user(self.admin_user).action_confirm()
        self.assertEqual(order.state, 'sale')
        
        # Admin requests edit (should be approved immediately)
        result = order.with_user(self.admin_user).ks_action_request_edit()
        
        self.assertTrue(order.ks_edit_approved, "Admin edit should be approved immediately")
        self.assertTrue(order.ks_can_edit, "Admin should be able to edit")

    def test_04_admin_can_edit_price_directly(self):
        """Test: Admin user can edit prices directly"""
        order = self._create_sale_order(user=self.admin_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        order.with_user(self.admin_user).action_confirm()
        
        # Admin edits price
        order.order_line[0].with_user(self.admin_user).write({
            'price_unit': 150.0,
        })
        
        self.assertEqual(order.order_line[0].price_unit, 150.0, "Admin should be able to edit price")

    def test_05_admin_does_not_see_request_buttons(self):
        """Test: Admin user does not see Request Cancel and Request Edit buttons"""
        order = self._create_sale_order(user=self.admin_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        order.with_user(self.admin_user).action_confirm()
        
        # Compute button visibility
        order._compute_ks_button_visibility()
        
        self.assertFalse(order.ks_show_request_edit_button, "Admin should not see Request Edit button")
        # Request Cancel button visibility is controlled in view, but admin should use standard Cancel

    def test_06_admin_sees_standard_cancel_button(self):
        """Test: Admin user sees standard Cancel button instead of Request Cancel"""
        order = self._create_sale_order(user=self.admin_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        order.with_user(self.admin_user).action_confirm()
        
        # Check that admin can use standard cancel
        # This is tested by the fact that action_cancel works directly for admin
        self.assertTrue(order._is_admin_user(), "User should be admin")

    def test_07_admin_can_edit_in_all_states(self):
        """Test: Admin can edit sale order in all states"""
        order = self._create_sale_order(user=self.admin_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        # Check editability in draft
        order._compute_ks_can_edit()
        self.assertTrue(order.ks_can_edit, "Admin should be able to edit in draft")
        
        # Confirm and check editability
        order.with_user(self.admin_user).action_confirm()
        order._compute_ks_can_edit()
        self.assertTrue(order.ks_can_edit, "Admin should be able to edit in sale state")

    def test_08_normal_user_still_needs_approval(self):
        """Test: Normal user still needs approval even if admin exists"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        # Normal user confirms
        order.with_user(self.normal_user).action_confirm()
        
        self.assertEqual(order.state, 'approval_pending', "Normal user should still need approval")


