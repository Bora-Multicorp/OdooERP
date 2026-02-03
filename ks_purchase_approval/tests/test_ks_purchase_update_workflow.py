# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from .common import KsPurchaseApprovalCommon


class TestKsPurchaseUpdateWorkflow(KsPurchaseApprovalCommon):
    """Test cases for PO Update Request Approval Workflow"""

    # ==================== POSITIVE TEST CASES ====================

    def test_01_normal_user_can_request_update(self):
        """POSITIVE: Normal user can request update for confirmed PO"""
        po = self._create_confirmed_po()
        self.assertEqual(po.state, 'purchase')
        
        # Normal user requests update
        po.with_user(self.normal_user).ks_do_request_update("Need to change quantity")
        
        self.assertEqual(po.state, 'update_requested', "PO should be in update_requested state")
        self.assertEqual(po.ks_update_request_user_id, self.normal_user)
        self.assertEqual(po.ks_update_request_reason, "Need to change quantity")
        self.assertTrue(po.ks_update_request_date)

    def test_02_pm1_can_approve_update(self):
        """POSITIVE: PM1 can approve update request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        # PM1 approves
        po.with_user(self.pm1_user).ks_action_approve_update()
        
        self.assertTrue(po.ks_update_pm1_approved)
        self.assertFalse(po.ks_update_pm2_approved)
        self.assertEqual(po.state, 'update_requested')

    def test_03_pm2_can_approve_update(self):
        """POSITIVE: PM2 can approve update request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        # PM2 approves
        po.with_user(self.pm2_user).ks_action_approve_update()
        
        self.assertFalse(po.ks_update_pm1_approved)
        self.assertTrue(po.ks_update_pm2_approved)
        self.assertEqual(po.state, 'update_requested')

    def test_04_both_pm_approve_enables_editing(self):
        """POSITIVE: When both PMs approve, PO becomes editable for requester"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        # Both PMs approve
        po.with_user(self.pm1_user).ks_action_approve_update()
        po.with_user(self.pm2_user).ks_action_approve_update()
        
        self.assertEqual(po.state, 'purchase')
        self.assertTrue(po.ks_update_approved, "Update should be approved")
        self.assertEqual(po.ks_update_request_user_id, self.normal_user)

    def test_05_requester_can_edit_after_update_approval(self):
        """POSITIVE: Requester can edit PO after update is approved"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        po.with_user(self.pm1_user).ks_action_approve_update()
        po.with_user(self.pm2_user).ks_action_approve_update()
        
        # Verify ks_can_edit is True for requester
        po_as_requester = po.with_user(self.normal_user)
        po_as_requester._compute_ks_can_edit()
        
        self.assertTrue(po_as_requester.ks_can_edit, "Requester should be able to edit")

    def test_06_requester_can_complete_update(self):
        """POSITIVE: Requester can complete update to lock PO again"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        po.with_user(self.pm1_user).ks_action_approve_update()
        po.with_user(self.pm2_user).ks_action_approve_update()
        
        self.assertTrue(po.ks_update_approved)
        
        # Complete update
        po.with_user(self.normal_user).ks_action_complete_update()
        
        self.assertFalse(po.ks_update_approved, "Update approved flag should be reset")
        self.assertFalse(po.ks_update_request_user_id, "Request user should be cleared")

    def test_07_pm1_can_reject_update(self):
        """POSITIVE: PM1 can reject update request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        # PM1 rejects
        po.with_user(self.pm1_user).ks_do_reject_update("Not allowed at this time")
        
        self.assertEqual(po.state, 'purchase', "PO should go back to purchase state")
        self.assertFalse(po.ks_update_approved)
        self.assertFalse(po.ks_update_request_user_id)

    def test_08_pm2_can_reject_update_after_pm1_approved(self):
        """POSITIVE: PM2 can reject update even after PM1 approved"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        # PM1 approves
        po.with_user(self.pm1_user).ks_action_approve_update()
        self.assertTrue(po.ks_update_pm1_approved)
        
        # PM2 rejects
        po.with_user(self.pm2_user).ks_do_reject_update("Rejected by PM2")
        
        self.assertEqual(po.state, 'purchase')
        self.assertFalse(po.ks_update_pm1_approved, "PM1 approval should be reset")

    def test_09_chatter_message_on_update_request(self):
        """POSITIVE: Chatter message is posted on update request"""
        po = self._create_confirmed_po()
        initial_message_count = len(po.message_ids)
        
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        self.assertGreater(len(po.message_ids), initial_message_count)

    def test_10_chatter_message_on_update_approval(self):
        """POSITIVE: Chatter message is posted on update approval"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        initial_message_count = len(po.message_ids)
        
        po.with_user(self.pm1_user).ks_action_approve_update()
        
        self.assertGreater(len(po.message_ids), initial_message_count)

    def test_11_chatter_message_on_update_rejection(self):
        """POSITIVE: Chatter message is posted on update rejection with reason"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        initial_message_count = len(po.message_ids)
        
        po.with_user(self.pm1_user).ks_do_reject_update("Rejection reason here")
        
        self.assertGreater(len(po.message_ids), initial_message_count)

    # ==================== NEGATIVE TEST CASES ====================

    def test_12_cannot_request_update_for_draft_po(self):
        """NEGATIVE: Cannot request update for draft PO"""
        po = self._create_purchase_order()
        self.assertEqual(po.state, 'draft')
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_request_update("Test reason")

    def test_13_cannot_request_update_for_pending_approval_po(self):
        """NEGATIVE: Cannot request update for PO in pending_approval"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        self.assertEqual(po.state, 'pending_approval')
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_request_update("Test reason")

    def test_14_cannot_request_update_without_reason(self):
        """NEGATIVE: Cannot request update without reason"""
        po = self._create_confirmed_po()
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_request_update("")

    def test_15_normal_user_cannot_approve_update(self):
        """NEGATIVE: Normal user cannot approve update request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_action_approve_update()

    def test_16_normal_user_cannot_reject_update(self):
        """NEGATIVE: Normal user cannot reject update request"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_reject_update("Any reason")

    def test_17_pm1_cannot_approve_update_twice(self):
        """NEGATIVE: PM1 cannot approve update twice"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        po.with_user(self.pm1_user).ks_action_approve_update()
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_action_approve_update()

    def test_18_cannot_approve_update_for_confirmed_po(self):
        """NEGATIVE: Cannot approve update for PO not in update_requested state"""
        po = self._create_confirmed_po()
        self.assertEqual(po.state, 'purchase')
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_action_approve_update()

    def test_19_rejection_without_reason_fails(self):
        """NEGATIVE: Update rejection without reason should fail"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_do_reject_update("")

    def test_20_other_user_cannot_complete_update(self):
        """NEGATIVE: User other than requester cannot complete update"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        po.with_user(self.pm1_user).ks_action_approve_update()
        po.with_user(self.pm2_user).ks_action_approve_update()
        
        # Another normal user tries to complete
        with self.assertRaises(UserError):
            po.with_user(self.normal_user_2).ks_action_complete_update()

    def test_21_cannot_complete_update_if_not_approved(self):
        """NEGATIVE: Cannot complete update if not approved"""
        po = self._create_confirmed_po()
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_action_complete_update()

    def test_22_cannot_request_update_while_update_pending(self):
        """NEGATIVE: Cannot request another update while one is pending"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("First request")
        
        self.assertEqual(po.state, 'update_requested')
        
        # Try to request another update - should fail because not in purchase state
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_request_update("Second request")

    def test_23_other_normal_user_cannot_edit_after_approval(self):
        """NEGATIVE: Other normal user cannot edit even after update approval"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        po.with_user(self.pm1_user).ks_action_approve_update()
        po.with_user(self.pm2_user).ks_action_approve_update()
        
        # Check ks_can_edit for another user
        po_as_other = po.with_user(self.normal_user_2)
        po_as_other._compute_ks_can_edit()
        
        self.assertFalse(po_as_other.ks_can_edit, "Other user should not be able to edit")



