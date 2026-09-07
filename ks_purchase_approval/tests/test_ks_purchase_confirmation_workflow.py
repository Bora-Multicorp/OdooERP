# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from .common import KsPurchaseApprovalCommon


class TestKsPurchaseConfirmationWorkflow(KsPurchaseApprovalCommon):
    """Test cases for PO Confirmation Approval Workflow"""

    # ==================== POSITIVE TEST CASES ====================

    def test_01_normal_user_confirm_goes_to_pending_approval(self):
        """POSITIVE: Normal user clicking Confirm Order sends PO to Pending Approval"""
        po = self._create_purchase_order()
        self.assertEqual(po.state, 'draft')
        
        # Normal user confirms
        po.with_user(self.normal_user).button_confirm()
        
        self.assertEqual(po.state, 'pending_approval', "PO should be in pending_approval state")
        self.assertEqual(po.ks_confirm_request_user_id, self.normal_user, "Request user should be set")
        self.assertTrue(po.ks_confirm_request_date, "Request date should be set")

    def test_02_pm_user_confirm_goes_directly_to_purchase(self):
        """POSITIVE: PM user clicking Confirm Order confirms PO immediately"""
        po = self._create_purchase_order(user=self.pm1_user)
        self.assertEqual(po.state, 'draft')
        
        # PM user confirms
        po.with_user(self.pm1_user).button_confirm()
        
        self.assertEqual(po.state, 'purchase', "PO should be confirmed immediately for PM user")

    def test_03_pm1_can_approve_confirmation(self):
        """POSITIVE: PM1 can approve confirmation request"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        # PM1 approves
        po.with_user(self.pm1_user).ks_action_approve_confirmation()
        
        self.assertTrue(po.ks_confirm_pm1_approved, "PM1 approval should be True")
        self.assertFalse(po.ks_confirm_pm2_approved, "PM2 approval should still be False")
        self.assertEqual(po.state, 'pending_approval', "PO should still be in pending_approval")

    def test_04_pm2_can_approve_confirmation(self):
        """POSITIVE: PM2 can approve confirmation request"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        # PM2 approves
        po.with_user(self.pm2_user).ks_action_approve_confirmation()
        
        self.assertFalse(po.ks_confirm_pm1_approved, "PM1 approval should still be False")
        self.assertTrue(po.ks_confirm_pm2_approved, "PM2 approval should be True")
        self.assertEqual(po.state, 'pending_approval', "PO should still be in pending_approval")

    def test_05_both_pm_approve_confirms_po(self):
        """POSITIVE: When both PM1 and PM2 approve, PO is confirmed"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        # PM1 approves
        po.with_user(self.pm1_user).ks_action_approve_confirmation()
        self.assertEqual(po.state, 'pending_approval')
        
        # PM2 approves
        po.with_user(self.pm2_user).ks_action_approve_confirmation()
        
        self.assertEqual(po.state, 'purchase', "PO should be confirmed after both approvals")
        self.assertTrue(po.date_approve, "Approval date should be set")

    def test_06_pm1_can_reject_confirmation(self):
        """POSITIVE: PM1 can reject confirmation with reason"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        # PM1 rejects
        po.with_user(self.pm1_user).ks_do_reject_confirmation("Budget exceeded")
        
        self.assertEqual(po.state, 'draft', "PO should go back to draft")
        self.assertFalse(po.ks_confirm_pm1_approved, "PM1 approval should be reset")
        self.assertFalse(po.ks_confirm_pm2_approved, "PM2 approval should be reset")

    def test_07_pm2_can_reject_confirmation_after_pm1_approved(self):
        """POSITIVE: PM2 can reject confirmation even after PM1 approved"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        # PM1 approves first
        po.with_user(self.pm1_user).ks_action_approve_confirmation()
        
        # PM2 rejects
        po.with_user(self.pm2_user).ks_do_reject_confirmation("Vendor not verified")
        
        self.assertEqual(po.state, 'draft', "PO should go back to draft")
        self.assertFalse(po.ks_confirm_pm1_approved, "PM1 approval should be reset")

    def test_08_approval_order_does_not_matter(self):
        """POSITIVE: PM2 can approve before PM1"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        # PM2 approves first
        po.with_user(self.pm2_user).ks_action_approve_confirmation()
        self.assertEqual(po.state, 'pending_approval')
        
        # PM1 approves second
        po.with_user(self.pm1_user).ks_action_approve_confirmation()
        
        self.assertEqual(po.state, 'purchase', "PO should be confirmed regardless of approval order")

    def test_09_chatter_message_on_confirmation_request(self):
        """POSITIVE: Chatter message is posted when confirmation is requested"""
        po = self._create_purchase_order()
        initial_message_count = len(po.message_ids)
        
        po.with_user(self.normal_user).button_confirm()
        
        self.assertGreater(len(po.message_ids), initial_message_count, "New message should be posted")

    def test_10_chatter_message_on_approval(self):
        """POSITIVE: Chatter message is posted when PM approves"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        initial_message_count = len(po.message_ids)
        
        po.with_user(self.pm1_user).ks_action_approve_confirmation()
        
        self.assertGreater(len(po.message_ids), initial_message_count, "Approval message should be posted")

    def test_11_chatter_message_on_rejection(self):
        """POSITIVE: Chatter message is posted when PM rejects with reason"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        initial_message_count = len(po.message_ids)
        
        po.with_user(self.pm1_user).ks_do_reject_confirmation("Test rejection reason")
        
        self.assertGreater(len(po.message_ids), initial_message_count, "Rejection message should be posted")

    # ==================== NEGATIVE TEST CASES ====================

    def test_12_normal_user_cannot_approve_confirmation(self):
        """NEGATIVE: Normal user cannot approve confirmation request"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_action_approve_confirmation()

    def test_13_normal_user_cannot_reject_confirmation(self):
        """NEGATIVE: Normal user cannot reject confirmation request"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        with self.assertRaises(UserError):
            po.with_user(self.normal_user).ks_do_reject_confirmation("Any reason")

    def test_14_pm1_cannot_approve_twice(self):
        """NEGATIVE: PM1 cannot approve the same request twice"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        # First approval
        po.with_user(self.pm1_user).ks_action_approve_confirmation()
        
        # Second approval attempt
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_action_approve_confirmation()

    def test_15_cannot_approve_draft_po(self):
        """NEGATIVE: Cannot approve a PO that is in draft state"""
        po = self._create_purchase_order()
        self.assertEqual(po.state, 'draft')
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_action_approve_confirmation()

    def test_16_cannot_approve_confirmed_po(self):
        """NEGATIVE: Cannot approve an already confirmed PO"""
        po = self._create_confirmed_po()
        self.assertEqual(po.state, 'purchase')
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_action_approve_confirmation()

    def test_17_rejection_without_reason_fails(self):
        """NEGATIVE: Rejection without reason should fail"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_do_reject_confirmation("")

    def test_18_rejection_with_empty_reason_fails(self):
        """NEGATIVE: Rejection with whitespace-only reason should fail"""
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        with self.assertRaises(UserError):
            po.with_user(self.pm1_user).ks_do_reject_confirmation("   ")

    def test_19_cannot_confirm_cancelled_po(self):
        """NEGATIVE: Cannot confirm a cancelled PO"""
        po = self._create_purchase_order()
        po.with_user(self.pm1_user).button_cancel()
        self.assertEqual(po.state, 'cancel')
        
        with self.assertRaises(Exception):
            po.with_user(self.normal_user).button_confirm()

    def test_20_other_pm_cannot_approve_if_not_configured(self):
        """NEGATIVE: A PM user not configured for confirmation cannot approve"""
        # Create a user who is PM but not configured for this company
        other_pm = self.env['res.users'].create({
            'name': 'Other PM',
            'login': 'other_pm',
            'email': 'other_pm@test.com',
            'company_id': self.company.id,
            'company_ids': [(4, self.company.id)],
            'groups_id': [(4, self.purchase_manager_group.id)],
        })
        
        po = self._create_purchase_order()
        po.with_user(self.normal_user).button_confirm()
        
        with self.assertRaises(UserError):
            po.with_user(other_pm).ks_action_approve_confirmation()

    def test_21_bill_to_contacts_computation(self):
        """TEST: Bill To field lists company contact and company warehouse contacts"""
        # Create warehouse for test company
        wh_partner = self.env['res.partner'].create({
            'name': 'Test WH Partner',
            'company_id': self.company.id,
        })
        warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
            'company_id': self.company.id,
            'partner_id': wh_partner.id,
        })

        po = self._create_purchase_order()
        self.assertIn(self.company.partner_id, po.bill_to_partner_ids, "Company partner should be in allowed Bill To contacts")
        self.assertIn(wh_partner, po.bill_to_partner_ids, "Warehouse partner should be in allowed Bill To contacts")




