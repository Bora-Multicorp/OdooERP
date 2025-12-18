# -*- coding: utf-8 -*-
from .common import KsPurchaseApprovalCommon


class TestKsButtonVisibility(KsPurchaseApprovalCommon):
    """Test cases for Button Visibility based on User Role and PO State"""

    # ==================== NORMAL USER BUTTON VISIBILITY ====================

    def test_01_normal_user_draft_po_button_visibility(self):
        """POSITIVE: Normal user sees correct buttons for draft PO"""
        po = self._create_purchase_order()
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_button_visibility()
        
        # Should NOT see PM buttons
        self.assertFalse(po_as_normal.ks_show_approve_confirm_button)
        self.assertFalse(po_as_normal.ks_show_reject_confirm_button)
        self.assertFalse(po_as_normal.ks_show_unlock_button)
        
        # Should NOT see request buttons (not confirmed yet)
        self.assertFalse(po_as_normal.ks_show_request_update_button)
        self.assertFalse(po_as_normal.ks_show_request_cancel_button)

    def test_02_normal_user_pending_approval_button_visibility(self):
        """POSITIVE: Normal user sees correct buttons for pending_approval PO"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_button_visibility()
        
        # Should NOT see any approval buttons
        self.assertFalse(po_as_normal.ks_show_approve_confirm_button)
        self.assertFalse(po_as_normal.ks_show_reject_confirm_button)
        
        # Should NOT see request buttons
        self.assertFalse(po_as_normal.ks_show_request_update_button)
        self.assertFalse(po_as_normal.ks_show_request_cancel_button)
        
        # Should NOT see unlock
        self.assertFalse(po_as_normal.ks_show_unlock_button)

    def test_03_normal_user_confirmed_po_button_visibility(self):
        """POSITIVE: Normal user sees Request Update/Cancel buttons for confirmed PO"""
        po = self._create_confirmed_po()
        
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_button_visibility()
        
        # Should see request buttons
        self.assertTrue(po_as_normal.ks_show_request_update_button)
        self.assertTrue(po_as_normal.ks_show_request_cancel_button)
        
        # Should NOT see PM buttons
        self.assertFalse(po_as_normal.ks_show_approve_confirm_button)
        self.assertFalse(po_as_normal.ks_show_unlock_button)

    def test_04_normal_user_never_sees_unlock_button(self):
        """NEGATIVE: Normal user NEVER sees Unlock button regardless of state"""
        # Test in various states
        
        # Draft
        po = self._create_purchase_order()
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_button_visibility()
        self.assertFalse(po_as_normal.ks_show_unlock_button, "No unlock in draft")
        
        # Pending Approval
        po.with_user(self.normal_user).button_confirm()
        po_as_normal._compute_ks_button_visibility()
        self.assertFalse(po_as_normal.ks_show_unlock_button, "No unlock in pending_approval")
        
        # Confirmed
        po.with_user(self.pm1_user).ks_action_approve_confirmation()
        po.with_user(self.pm2_user).ks_action_approve_confirmation()
        po_as_normal._compute_ks_button_visibility()
        self.assertFalse(po_as_normal.ks_show_unlock_button, "No unlock in purchase")
        
        # Locked
        po.with_user(self.pm1_user).button_done()
        po_as_normal._compute_ks_button_visibility()
        self.assertFalse(po_as_normal.ks_show_unlock_button, "No unlock in done")

    def test_05_normal_user_sees_complete_update_button_after_approval(self):
        """POSITIVE: Normal user sees Complete Update button after update approval"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        po.with_user(self.pm1_user).ks_action_approve_update()
        po.with_user(self.pm2_user).ks_action_approve_update()
        
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_button_visibility()
        
        self.assertTrue(po_as_normal.ks_show_complete_update_button)
        # Request Update should be hidden while in edit mode
        self.assertFalse(po_as_normal.ks_show_request_update_button)

    def test_06_other_normal_user_does_not_see_complete_update(self):
        """NEGATIVE: Other normal user does NOT see Complete Update button"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        po.with_user(self.pm1_user).ks_action_approve_update()
        po.with_user(self.pm2_user).ks_action_approve_update()
        
        po_as_other = po.with_user(self.normal_user_2)
        po_as_other._compute_ks_button_visibility()
        
        self.assertFalse(po_as_other.ks_show_complete_update_button)

    # ==================== PM USER BUTTON VISIBILITY ====================

    def test_07_pm_user_draft_po_button_visibility(self):
        """POSITIVE: PM user sees correct buttons for draft PO"""
        po = self._create_purchase_order()
        po_as_pm = po.with_user(self.pm1_user)
        po_as_pm._compute_ks_button_visibility()
        
        # Should NOT see approval buttons for draft
        self.assertFalse(po_as_pm.ks_show_approve_confirm_button)
        self.assertFalse(po_as_pm.ks_show_reject_confirm_button)
        
        # Should NOT see request buttons (PM doesn't need them)
        self.assertFalse(po_as_pm.ks_show_request_update_button)
        self.assertFalse(po_as_pm.ks_show_request_cancel_button)

    def test_08_pm_user_pending_approval_button_visibility(self):
        """POSITIVE: PM user sees Approve/Reject buttons for pending_approval PO"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        po_as_pm1 = po.with_user(self.pm1_user)
        po_as_pm1._compute_ks_button_visibility()
        
        # PM1 should see approval buttons
        self.assertTrue(po_as_pm1.ks_show_approve_confirm_button)
        self.assertTrue(po_as_pm1.ks_show_reject_confirm_button)
        
        # PM2 should also see approval buttons
        po_as_pm2 = po.with_user(self.pm2_user)
        po_as_pm2._compute_ks_button_visibility()
        self.assertTrue(po_as_pm2.ks_show_approve_confirm_button)
        self.assertTrue(po_as_pm2.ks_show_reject_confirm_button)

    def test_09_pm_user_no_approval_buttons_after_approving(self):
        """POSITIVE: PM user does NOT see approval buttons after already approving"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        # PM1 approves
        po.with_user(self.pm1_user).ks_action_approve_confirmation()
        
        po_as_pm1 = po.with_user(self.pm1_user)
        po_as_pm1._compute_ks_button_visibility()
        
        # PM1 should NOT see approval buttons anymore
        self.assertFalse(po_as_pm1.ks_show_approve_confirm_button)
        self.assertFalse(po_as_pm1.ks_show_reject_confirm_button)
        
        # But PM2 should still see them
        po_as_pm2 = po.with_user(self.pm2_user)
        po_as_pm2._compute_ks_button_visibility()
        self.assertTrue(po_as_pm2.ks_show_approve_confirm_button)
        self.assertTrue(po_as_pm2.ks_show_reject_confirm_button)

    def test_10_pm_user_sees_unlock_button_for_done_po(self):
        """POSITIVE: PM user sees Unlock button for locked (done) PO"""
        po = self._create_confirmed_po()
        po.with_user(self.pm1_user).button_done()
        self.assertEqual(po.state, 'done')
        
        po_as_pm = po.with_user(self.pm1_user)
        po_as_pm._compute_ks_button_visibility()
        
        self.assertTrue(po_as_pm.ks_show_unlock_button)

    def test_11_pm_user_update_requested_button_visibility(self):
        """POSITIVE: PM user sees Approve/Reject Update buttons"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        po_as_pm1 = po.with_user(self.pm1_user)
        po_as_pm1._compute_ks_button_visibility()
        
        self.assertTrue(po_as_pm1.ks_show_approve_update_button)
        self.assertTrue(po_as_pm1.ks_show_reject_update_button)

    def test_12_pm_user_cancel_requested_button_visibility(self):
        """POSITIVE: PM user sees Approve/Reject Cancel buttons"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        po_as_pm1 = po.with_user(self.pm1_user)
        po_as_pm1._compute_ks_button_visibility()
        
        self.assertTrue(po_as_pm1.ks_show_approve_cancel_button)
        self.assertTrue(po_as_pm1.ks_show_reject_cancel_button)

    def test_13_pm_user_does_not_see_request_buttons(self):
        """NEGATIVE: PM user NEVER sees Request Update/Cancel buttons"""
        po = self._create_confirmed_po()
        
        po_as_pm = po.with_user(self.pm1_user)
        po_as_pm._compute_ks_button_visibility()
        
        self.assertFalse(po_as_pm.ks_show_request_update_button)
        self.assertFalse(po_as_pm.ks_show_request_cancel_button)

    # ==================== CAN EDIT TESTS ====================

    def test_14_normal_user_can_edit_draft_po(self):
        """POSITIVE: Normal user can edit draft PO"""
        po = self._create_purchase_order()
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_can_edit()
        
        self.assertTrue(po_as_normal.ks_can_edit)

    def test_15_normal_user_cannot_edit_pending_approval_po(self):
        """NEGATIVE: Normal user CANNOT edit pending_approval PO"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_can_edit()
        
        self.assertFalse(po_as_normal.ks_can_edit)

    def test_16_normal_user_cannot_edit_confirmed_po(self):
        """NEGATIVE: Normal user CANNOT edit confirmed PO"""
        po = self._create_confirmed_po()
        
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_can_edit()
        
        self.assertFalse(po_as_normal.ks_can_edit)

    def test_17_normal_user_can_edit_after_update_approval(self):
        """POSITIVE: Normal user CAN edit after update approval"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        po.with_user(self.pm1_user).ks_action_approve_update()
        po.with_user(self.pm2_user).ks_action_approve_update()
        
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_can_edit()
        
        self.assertTrue(po_as_normal.ks_can_edit)

    def test_18_pm_user_can_edit_confirmed_po(self):
        """POSITIVE: PM user CAN edit confirmed PO"""
        po = self._create_confirmed_po()
        
        po_as_pm = po.with_user(self.pm1_user)
        po_as_pm._compute_ks_can_edit()
        
        self.assertTrue(po_as_pm.ks_can_edit)

    def test_19_pm_user_cannot_edit_locked_po(self):
        """NEGATIVE: PM user CANNOT edit locked (done) PO"""
        po = self._create_confirmed_po()
        po.with_user(self.pm1_user).button_done()
        
        po_as_pm = po.with_user(self.pm1_user)
        po_as_pm._compute_ks_can_edit()
        
        self.assertFalse(po_as_pm.ks_can_edit)

    def test_20_is_pm_user_computed_correctly(self):
        """POSITIVE: ks_is_pm_user computed correctly"""
        po = self._create_purchase_order()
        
        # For PM user
        po_as_pm = po.with_user(self.pm1_user)
        po_as_pm._compute_ks_is_pm_user()
        self.assertTrue(po_as_pm.ks_is_pm_user)
        self.assertFalse(po_as_pm.ks_is_normal_user)
        
        # For normal user
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_is_pm_user()
        self.assertFalse(po_as_normal.ks_is_pm_user)
        self.assertTrue(po_as_normal.ks_is_normal_user)

    def test_21_normal_user_cannot_edit_update_requested_po(self):
        """NEGATIVE: Normal user CANNOT edit update_requested PO"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_update("Test reason")
        
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_can_edit()
        
        self.assertFalse(po_as_normal.ks_can_edit)

    def test_22_normal_user_cannot_edit_cancel_requested_po(self):
        """NEGATIVE: Normal user CANNOT edit cancel_requested PO"""
        po = self._create_confirmed_po()
        po.with_user(self.normal_user).ks_do_request_cancel("Test reason")
        
        po_as_normal = po.with_user(self.normal_user)
        po_as_normal._compute_ks_can_edit()
        
        self.assertFalse(po_as_normal.ks_can_edit)



