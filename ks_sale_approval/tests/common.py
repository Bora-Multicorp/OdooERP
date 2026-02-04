# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields


class KsSaleApprovalCommon(TransactionCase):
    """Common setup for Sale Approval tests"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Get existing groups
        cls.sales_user_group = cls.env.ref('sales_team.group_sale_salesman')
        cls.sales_manager_group = cls.env.ref('sales_team.group_sale_manager')
        cls.admin_group = cls.env.ref('base.group_system')
        
        # Create test company
        cls.company = cls.env['res.company'].create({
            'name': 'Test Sale Approval Company',
        })
        
        # Create PM1 Users (Approval Manager 1) - Multiple users for multi-user selection
        cls.pm1_user_1 = cls.env['res.users'].create({
            'name': 'PM1 Approver 1',
            'login': 'pm1_approver_1',
            'email': 'pm1_1@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.sales_manager_group.id)],
        })
        
        cls.pm1_user_2 = cls.env['res.users'].create({
            'name': 'PM1 Approver 2',
            'login': 'pm1_approver_2',
            'email': 'pm1_2@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.sales_manager_group.id)],
        })
        
        # Create PM2 Users (Approval Manager 2) - Multiple users for multi-user selection
        cls.pm2_user_1 = cls.env['res.users'].create({
            'name': 'PM2 Approver 1',
            'login': 'pm2_approver_1',
            'email': 'pm2_1@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.sales_manager_group.id)],
        })
        
        cls.pm2_user_2 = cls.env['res.users'].create({
            'name': 'PM2 Approver 2',
            'login': 'pm2_approver_2',
            'email': 'pm2_2@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.sales_manager_group.id)],
        })
        
        # Create Normal User (Sales User, not a PM)
        cls.normal_user = cls.env['res.users'].create({
            'name': 'Normal Sale User',
            'login': 'normal_sale_user',
            'email': 'normal@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.sales_user_group.id)],
        })
        
        # Create Admin User
        cls.admin_user = cls.env['res.users'].create({
            'name': 'Admin User',
            'login': 'admin_user',
            'email': 'admin@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
            'groups_id': [(4, cls.admin_group.id)],
        })
        
        # Create Customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'customer_rank': 1,
            'company_id': cls.company.id,
        })
        
        # Create Product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'sale_ok': True,
            'list_price': 100.0,
        })
        
        # Create Approval Configuration - Single Approval Mode
        cls.approval_config_single = cls.env['ks.sale.approval.config'].create({
            'company_id': cls.company.id,
            'ks_approval_mode': 'single',
            'ks_confirm_pm1_ids': [(6, 0, [cls.pm1_user_1.id, cls.pm1_user_2.id])],
            'ks_confirm_pm2_ids': [(6, 0, [])],
            'ks_cancel_pm1_ids': [(6, 0, [cls.pm1_user_1.id, cls.pm1_user_2.id])],
            'ks_cancel_pm2_ids': [(6, 0, [])],
            'ks_edit_pm1_ids': [(6, 0, [cls.pm1_user_1.id, cls.pm1_user_2.id])],
            'ks_edit_pm2_ids': [(6, 0, [])],
        })
        
        # Create Approval Configuration - Dual Approval Mode
        cls.approval_config_dual = cls.env['ks.sale.approval.config'].create({
            'company_id': cls.company.id,
            'ks_approval_mode': 'dual',
            'ks_confirm_pm1_ids': [(6, 0, [cls.pm1_user_1.id, cls.pm1_user_2.id])],
            'ks_confirm_pm2_ids': [(6, 0, [cls.pm2_user_1.id, cls.pm2_user_2.id])],
            'ks_cancel_pm1_ids': [(6, 0, [cls.pm1_user_1.id, cls.pm1_user_2.id])],
            'ks_cancel_pm2_ids': [(6, 0, [cls.pm2_user_1.id, cls.pm2_user_2.id])],
            'ks_edit_pm1_ids': [(6, 0, [cls.pm1_user_1.id, cls.pm1_user_2.id])],
            'ks_edit_pm2_ids': [(6, 0, [cls.pm2_user_1.id, cls.pm2_user_2.id])],
        })

    def _create_sale_order(self, user=None, state='draft'):
        """Helper method to create a sale order"""
        if user is None:
            user = self.normal_user
        
        order = self.env['sale.order'].with_user(user).with_company(self.company).create({
            'partner_id': self.customer.id,
            'company_id': self.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 10.0,
                'price_unit': 100.0,
            })],
        })
        
        if state == 'sent':
            order.action_quotation_sent()
        elif state == 'sale':
            # For confirmed state, we need to go through approval workflow
            # This will be handled in workflow tests
            pass
        
        return order

