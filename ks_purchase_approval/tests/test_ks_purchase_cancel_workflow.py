# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from .common import KsPurchaseApprovalCommon


class TestKsPurchaseCancelWorkflow(KsPurchaseApprovalCommon):
    """Test cases for PO Cancel Request Approval Workflow"""

    # ==================== POSITIVE TEST CASES ====================

    def test_01_normal_user_can_request_cancel(self):
        """POSITIVE: Normal user can request cancellation for confirmed PO"""
        po = self._create_confirmed_po()
        self.assertEqual(po.state, 'purchase')
        
        # Normal user requests cancel
        po.with_user(self.normal_user).ks_do_request_cancel("Order no longer needed")
        
        self.assertEqual(po.state, 'cancel_requested')
        self.assertEqual(po.ks_cancel_request_user_id, self.normal_user)
        self.assertEqual(po.ks_cancel_request_reason, "Order no longer needed")
        self.assertTrue(po.ks_cancel_request_date)

    def test_02_pm1_can_approve_cancel(self):
        """POSITIVE: PM1 can approve cancel request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        # PM1 approves
        po.with_user(self.pm1_user).ks_action_approve_cancel()
        
        self.assertTrue(po.ks_cancel_pm1_approved)
        self.assertFalse(po.ks_cancel_pm2_approved)
        self.assertEqual(po.state, 'cancel_requested')

    def test_03_pm2_can_approve_cancel(self):
        """POSITIVE: PM2 can approve cancel request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        # PM2 approves
        po.with_user(self.pm2_user).ks_action_approve_cancel()
        
        self.assertFalse(po.ks_cancel_pm1_approved)
        self.assertTrue(po.ks_cancel_pm2_approved)
        self.assertEqual(po.state, 'cancel_requested')

    def test_04_both_pm_approve_cancels_po(self):
        """POSITIVE: When both PMs approve, PO is cancelled"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        # Both PMs approve
        po.with_user(self.pm1_user).ks_action_approve_cancel()
        po.with_user(self.pm2_user).ks_action_approve_cancel()
        
        self.assertEqual(po.state, 'cancel', "PO should be cancelled")

    def test_05_pm1_can_reject_cancel(self):
        """POSITIVE: PM1 can reject cancel request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        # PM1 rejects
        po.with_user(self.pm1_user).ks_do_reject_cancel("Cannot cancel - goods already shipped")
        
        self.assertEqual(po.state, 'purchase', "PO should go back to purchase state")
        self.assertFalse(po.ks_cancel_pm1_approved)
        self.assertFalse(po.ks_cancel_request_user_id)

    def test_06_pm2_can_reject_cancel_after_pm1_approved(self):
        """POSITIVE: PM2 can reject cancel even after PM1 approved"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        # PM1 approves
        po.with_user(self.pm1_user).ks_action_approve_cancel()
        self.assertTrue(po.ks_cancel_pm1_approved)
        
        # PM2 rejects
        po.with_user(self.pm2_user).ks_do_reject_cancel("Rejected by PM2")
        
        self.assertEqual(po.state, 'purchase')
        self.assertFalse(po.ks_cancel_pm1_approved, "PM1 approval should be reset")

    def test_07_pm_can_directly_cancel_draft_po(self):
        """POSITIVE: PM can directly cancel a draft PO"""
        po = self._create_purchase_order(user=self.pm1_user)
        self.assertEqual(po.state, 'draft')
        
        po.with_user(self.pm1_user).button_cancel()
        
        self.assertEqual(po.state, 'cancel')

    def test_08_pm_can_directly_cancel_confirmed_po(self):
        """POSITIVE: PM can directly cancel a confirmed PO"""
        po = self._create_confirmed_po()
        self.assertEqual(po.state, 'purchase')
        
        po.with_user(self.pm1_user).button_cancel()
        
        self.assertEqual(po.state, 'cancel')

    def test_09_normal_user_can_directly_cancel_draft_po(self):
        """POSITIVE: Normal user can directly cancel a draft PO"""
        po = self._create_purchase_order()
        self.assertEqual(po.state, 'draft')
        
        po.with_user(self.normal_user).button_cancel()
        
        self.assertEqual(po.state, 'cancel')

    def test_10_chatter_message_on_cancel_request(self):
        """POSITIVE: Chatter message is posted on cancel request"""
        po = self._create_confirmed_po()
        initial_message_count = len(po.message_ids)
        
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        self.assertGreater(len(po.message_ids), initial_message_count)

    def test_11_chatter_message_on_cancel_approval(self):
        """POSITIVE: Chatter message is posted on cancel approval"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        initial_message_count = len(po.message_ids)
        
        po.with_user(self.pm1_user).ks_action_approve_cancel()
        
        self.assertGreater(len(po.message_ids), initial_message_count)

    def test_12_chatter_message_on_cancel_rejection(self):
        """POSITIVE: Chatter message is posted on cancel rejection"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        initial_message_count = len(po.message_ids)
        
        po.with_user(self.pm1_user).ks_do_reject_cancel("Rejection reason")
        
        self.assertGreater(len(po.message_ids), initial_message_count)

    def test_13_cancel_approval_order_does_not_matter(self):
        """POSITIVE: PM2 can approve before PM1 for cancel"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        # PM2 approves first
        po.with_user(self.pm2_user).ks_action_approve_cancel()
        self.assertEqual(po.state, 'cancel_requested')
        
        # PM1 approves second
        po.with_user(self.pm1_user).ks_action_approve_cancel()
        
        self.assertEqual(po.state, 'cancel')

    # ==================== NEGATIVE TEST CASES ====================

    def test_14_cannot_request_cancel_for_draft_po(self):
        """NEGATIVE: Cannot request cancel for draft PO (use direct cancel instead)"""
        po = self._create_purchase_order()
        self.assertEqual(po.state, 'draft')
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_request_cancel("Test reason")

    def test_15_cannot_request_cancel_for_pending_approval_po(self):
        """NEGATIVE: Cannot request cancel for PO in pending_approval"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        self.assertEqual(po.state, 'pending_approval')
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_request_cancel("Test reason")

    def test_16_cannot_request_cancel_without_reason(self):
        """NEGATIVE: Cannot request cancel without reason"""
        po = self._create_confirmed_po()
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_request_cancel("")

    def test_17_normal_user_cannot_approve_cancel(self):
        """NEGATIVE: Normal user cannot approve cancel request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_action_approve_cancel()

    def test_18_normal_user_cannot_reject_cancel(self):
        """NEGATIVE: Normal user cannot reject cancel request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_reject_cancel("Any reason")

    def test_19_pm1_cannot_approve_cancel_twice(self):
        """NEGATIVE: PM1 cannot approve cancel twice"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        po.with_user(self.pm1_user).ks_action_approve_cancel()
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_action_approve_cancel()

    def test_20_cannot_approve_cancel_for_confirmed_po(self):
        """NEGATIVE: Cannot approve cancel for PO not in cancel_requested state"""
        po = self._create_confirmed_po()
        self.assertEqual(po.state, 'purchase')
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_action_approve_cancel()

    def test_21_rejection_without_reason_fails(self):
        """NEGATIVE: Cancel rejection without reason should fail"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_do_reject_cancel("")

    def test_22_cannot_request_cancel_while_cancel_pending(self):
        """NEGATIVE: Cannot request another cancel while one is pending"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("First request")
        
        self.assertEqual(po.state, 'cancel_requested')
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_request_cancel("Second request")

    def test_23_cannot_request_cancel_for_already_cancelled_po(self):
        """NEGATIVE: Cannot request cancel for already cancelled PO"""
        po = self._create_confirmed_po()
        po.with_user(self.pm1_user).button_cancel()
        self.assertEqual(po.state, 'cancel')
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_request_cancel("Test reason")

    def test_24_other_pm_cannot_approve_if_not_configured(self):
        """NEGATIVE: A PM user not configured for cancel cannot approve"""
        # Create a user who is PM but not configured for this company
        other_pm = self.env['res.users'].create({
            'name': 'Other PM for Cancel',
            'login': 'other_pm_cancel',
            'email': 'other_pm_cancel@test.com',
            'company_id': self.company.id,
            'company_ids': [(4, self.company.id)],
            'groups_id': [(4, self.purchase_manager_group.id)],
        })
        
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        with self.assertRaises(UserError):
            po.with_user(other_pm).ks_action_approve_cancel()



