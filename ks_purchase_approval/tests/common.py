# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields


class KsPurchaseApprovalCommon(TransactionCase):
    """Common setup for Purchase Approval tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Get existing groups
        cls.purchase_user_group = cls.env.ref('purchase.group_purchase_user')
        cls.purchase_manager_group = cls.env.ref('purchase.group_purchase_manager')
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Approval Company',
        })
        
        # Create PM1 User (Approval Manager 1)
        cls.pm1_user = cls.env['res.users'].create({
            'name': 'PM1 Approver',
            'login': 'pm1_approver',
            'email': 'pm1@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.purchase_manager_group.id)],
        })
        
        # Create PM2 User (Approval Manager 2)
        cls.pm2_user = cls.env['res.users'].create({
            'name': 'PM2 Approver',
            'login': 'pm2_approver',
            'email': 'pm2@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.purchase_manager_group.id)],
        })
        
        # Create Normal User (Purchase User, not a PM)
        cls.normal_user = cls.env['res.users'].create({
            'name': 'Normal Purchase User',
            'login': 'normal_purchase_user',
            'email': 'normal@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.purchase_user_group.id)],
        })
        
        # Create another normal user for testing
        cls.normal_user_2 = cls.env['res.users'].create({
            'name': 'Normal Purchase User 2',
            'login': 'normal_purchase_user_2',
            'email': 'normal2@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.purchase_user_group.id)],
        })
        
        # Create Vendor
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor',
            'supplier_rank': 1,
            'company_id': cls.company.id,
        })
        
        # Create Product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'consu',
            'purchase_ok': True,
            'standard_price': 100.0,
        })
        
        # Create Approval Configuration
        cls.approval_config = cls.env['ks.purchase.approval.config'].create({
            'company_id': cls.company.id,
            'ks_confirm_pm1_id': cls.pm1_user.id,
            'ks_confirm_pm2_id': cls.pm2_user.id,
            'ks_update_pm1_id': cls.pm1_user.id,
            'ks_update_pm2_id': cls.pm2_user.id,
            'ks_cancel_pm1_id': cls.pm1_user.id,
            'ks_cancel_pm2_id': cls.pm2_user.id,
        })

    def _create_purchase_order(self, user=None):
        """Helper method to create a purchase order"""
        if user is None:
            user = self.normal_user
        
        return self.env['purchase.order'].with_user(user).with_company(self.company).create({
            'partner_id': self.vendor.id,
            'company_id': self.company.id,
            'bill_to_id': self.company.partner_id.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 10.0,
                'price_unit': 100.0,
                'name': self.product.name,
                'date_planned': fields.Datetime.now(),
            })],
        })

    def _create_confirmed_po(self, user=None):
        """Helper method to create a confirmed PO (approved by both PMs)"""
        po = self._create_purchase_order(user)
        
        # Normal user confirms -> goes to pending_approval
        po.with_user(self.normal_user).button_confirm()
        
        # PM1 approves
        po.with_user(self.pm1_user).ks_action_approve_confirmation()
        
        # PM2 approves -> PO confirmed
        po.with_user(self.pm2_user).ks_action_approve_confirmation()
        
        return po



