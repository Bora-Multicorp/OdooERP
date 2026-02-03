# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from .common import KsSaleApprovalCommon


class TestKsSaleApprovalWorkflow(KsSaleApprovalCommon):
    """Test cases for Sale Approval Workflow"""

    def test_01_normal_user_confirmation_goes_to_approval_pending_single(self):
        """Test: Normal user confirmation goes to approval_pending in single mode"""
        order = self._create_sale_order(user=self.normal_user)
        
        # Set company config to single approval
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        # Normal user tries to confirm
        order.with_user(self.normal_user).action_confirm()
        
        self.assertEqual(order.state, 'approval_pending', "Order should be in approval_pending state")
        self.assertFalse(order.ks_confirm_pm1_approved, "PM1 should not be approved yet")

    def test_02_pm1_approval_confirms_order_single_mode(self):
        """Test: PM1 approval confirms order in single approval mode"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        # Normal user confirms -> goes to approval_pending
        order.with_user(self.normal_user).action_confirm()
        
        # Create approval request wizard to select approvers
        wizard = self.env['ks.sale.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
            'ks_approver1_user': self.pm1_user_1.id,
        })
        wizard.action_confirm_request()
        
        # PM1 approves
        order.with_user(self.pm1_user_1).ks_action_approve_confirmation()
        
        self.assertEqual(order.state, 'sale', "Order should be confirmed after PM1 approval in single mode")
        self.assertTrue(order.ks_confirm_pm1_approved, "PM1 should be marked as approved")

    def test_03_dual_approval_requires_both_pms(self):
        """Test: Dual approval requires both PM1 and PM2 to approve"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_dual.id
        
        # Normal user confirms -> goes to approval_pending
        order.with_user(self.normal_user).action_confirm()
        
        # Create approval request wizard to select approvers
        wizard = self.env['ks.sale.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
            'ks_approver1_user': self.pm1_user_1.id,
            'ks_approver2_user': self.pm2_user_1.id,
        })
        wizard.action_confirm_request()
        
        # PM1 approves
        order.with_user(self.pm1_user_1).ks_action_approve_confirmation()
        self.assertEqual(order.state, 'approval_pending', "Order should still be pending after PM1 approval")
        
        # PM2 approves
        order.with_user(self.pm2_user_1).ks_action_approve_confirmation()
        self.assertEqual(order.state, 'sale', "Order should be confirmed after both PMs approve")

    def test_04_pm2_cannot_approve_before_pm1(self):
        """Test: PM2 cannot approve before PM1 in dual mode"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_dual.id
        
        order.with_user(self.normal_user).action_confirm()
        
        wizard = self.env['ks.sale.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
            'ks_approver1_user': self.pm1_user_1.id,
            'ks_approver2_user': self.pm2_user_1.id,
        })
        wizard.action_confirm_request()
        
        # PM2 tries to approve before PM1
        order.with_user(self.pm2_user_1).ks_action_approve_confirmation()
        
        # PM2 should not be able to approve
        self.assertFalse(order.ks_confirm_pm2_approved, "PM2 should not be approved before PM1")
        self.assertEqual(order.state, 'approval_pending', "Order should still be pending")

    def test_05_cancel_request_workflow(self):
        """Test: Cancel request workflow"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        # First confirm the order
        order.with_user(self.normal_user).action_confirm()
        wizard = self.env['ks.sale.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
            'ks_approver1_user': self.pm1_user_1.id,
        })
        wizard.action_confirm_request()
        order.with_user(self.pm1_user_1).ks_action_approve_confirmation()
        
        # Now request cancel
        cancel_wizard = self.env['ks.sale.cancel.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
            'ks_approver1_user': self.pm1_user_1.id,
        })
        cancel_wizard.action_confirm_request()
        
        self.assertEqual(order.state, 'cancel_pending', "Order should be in cancel_pending state")

    def test_06_edit_request_workflow(self):
        """Test: Edit request workflow"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        # First confirm the order
        order.with_user(self.normal_user).action_confirm()
        wizard = self.env['ks.sale.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
            'ks_approver1_user': self.pm1_user_1.id,
        })
        wizard.action_confirm_request()
        order.with_user(self.pm1_user_1).ks_action_approve_confirmation()
        
        # Now request edit
        edit_wizard = self.env['ks.sale.edit.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
            'ks_approver1_user': self.pm1_user_1.id,
        })
        edit_wizard.action_confirm_request()
        
        self.assertEqual(order.state, 'edit_pending', "Order should be in edit_pending state")

    def test_07_reject_confirmation_with_reason(self):
        """Test: PM can reject confirmation with reason"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        order.with_user(self.normal_user).action_confirm()
        
        wizard = self.env['ks.sale.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
            'ks_approver1_user': self.pm1_user_1.id,
        })
        wizard.action_confirm_request()
        
        # PM1 rejects
        reject_wizard = self.env['ks.sale.reject.reason.wizard'].with_user(self.pm1_user_1).create({
            'sale_order_id': order.id,
            'rejection_reason': 'Insufficient information',
        })
        reject_wizard.action_reject()
        
        self.assertEqual(order.state, 'draft', "Order should return to draft after rejection")

    def test_08_multi_user_selection_in_wizard(self):
        """Test: User can select from multiple PM users in wizard"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        order.with_user(self.normal_user).action_confirm()
        
        wizard = self.env['ks.sale.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
        })
        
        # Check that multiple users are available
        self.assertGreaterEqual(len(wizard.ks_approver1_user_ids), 2, "Should have multiple PM1 users available")
        self.assertIn(self.pm1_user_1, wizard.ks_approver1_user_ids)
        self.assertIn(self.pm1_user_2, wizard.ks_approver1_user_ids)

    def test_09_approver_selection_excludes_overlap(self):
        """Test: Selecting approver1 removes them from approver2 options"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_dual.id
        
        order.with_user(self.normal_user).action_confirm()
        
        wizard = self.env['ks.sale.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
            'ks_approver1_user': self.pm1_user_1.id,
        })
        
        # After selecting PM1 user, they should not be available for PM2
        self.assertNotIn(self.pm1_user_1, wizard.ks_approver2_filtered_ids, 
                        "Selected PM1 user should not be available for PM2")

    def test_10_single_approval_hides_pm2_fields(self):
        """Test: Single approval mode hides PM2 fields"""
        order = self._create_sale_order(user=self.normal_user)
        self.company.ks_sale_approval_config_id = self.approval_config_single.id
        
        order.with_user(self.normal_user).action_confirm()
        
        wizard = self.env['ks.sale.approval.request.wizard'].with_user(self.normal_user).create({
            'sale_order_id': order.id,
        })
        
        self.assertFalse(wizard.ks_show_approver2, "PM2 should be hidden in single approval mode")

