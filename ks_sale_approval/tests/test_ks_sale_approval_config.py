# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestKsSaleApprovalConfig(TransactionCase):
    """Test cases for Sale Approval Configuration Model"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        cls.company = cls.env['res.company'].create({
            'name': 'Test Config Company',
        })
        
        cls.user_1 = cls.env['res.users'].create({
            'name': 'Test User 1',
            'login': 'test_user_1',
            'email': 'user1@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
        })
        
        cls.user_2 = cls.env['res.users'].create({
            'name': 'Test User 2',
            'login': 'test_user_2',
            'email': 'user2@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
        })
        
        cls.user_3 = cls.env['res.users'].create({
            'name': 'Test User 3',
            'login': 'test_user_3',
            'email': 'user3@test.com',
            'company_id': cls.company.id,
            'company_ids': [(4, cls.company.id)],
        })

    # ==================== POSITIVE TEST CASES ====================

    def test_01_create_config_with_multiple_pm_users(self):
        """POSITIVE: Create configuration with multiple PM1 and PM2 users"""
        config = self.env['ks.sale.approval.config'].create({
            'company_id': self.company.id,
            'ks_approval_mode': 'single',
            'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id, self.user_2.id])],
            'ks_confirm_pm2_ids': [(6, 0, [])],
            'ks_cancel_pm1_ids': [(6, 0, [self.user_1.id, self.user_2.id])],
            'ks_cancel_pm2_ids': [(6, 0, [])],
            'ks_edit_pm1_ids': [(6, 0, [self.user_1.id, self.user_2.id])],
            'ks_edit_pm2_ids': [(6, 0, [])],
        })
        
        self.assertTrue(config.id, "Configuration should be created successfully")
        self.assertEqual(len(config.ks_confirm_pm1_ids), 2, "Should have 2 PM1 users")
        self.assertIn(self.user_1, config.ks_confirm_pm1_ids)
        self.assertIn(self.user_2, config.ks_confirm_pm1_ids)

    def test_02_create_config_dual_approval_mode(self):
        """POSITIVE: Create configuration with dual approval mode"""
        config = self.env['ks.sale.approval.config'].create({
            'company_id': self.company.id,
            'ks_approval_mode': 'dual',
            'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_confirm_pm2_ids': [(6, 0, [self.user_2.id])],
            'ks_cancel_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_cancel_pm2_ids': [(6, 0, [self.user_2.id])],
            'ks_edit_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_edit_pm2_ids': [(6, 0, [self.user_2.id])],
        })
        
        self.assertTrue(config.id, "Configuration should be created successfully")
        self.assertEqual(config.ks_approval_mode, 'dual')
        self.assertTrue(config.is_dual_approval(), "Should return True for dual approval")

    def test_03_get_config_returns_correct_company_config(self):
        """POSITIVE: get_config() returns the correct company configuration"""
        config = self.env['ks.sale.approval.config'].create({
            'company_id': self.company.id,
            'ks_approval_mode': 'single',
            'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_cancel_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_edit_pm1_ids': [(6, 0, [self.user_1.id])],
        })
        
        retrieved_config = self.env['ks.sale.approval.config'].get_config(self.company.id)
        
        self.assertEqual(config.id, retrieved_config.id, "Should retrieve the same configuration")

    def test_04_get_all_pm_users_returns_all_configured_pms(self):
        """POSITIVE: get_all_pm_users() returns all PM users"""
        config = self.env['ks.sale.approval.config'].create({
            'company_id': self.company.id,
            'ks_approval_mode': 'dual',
            'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_confirm_pm2_ids': [(6, 0, [self.user_2.id])],
            'ks_cancel_pm1_ids': [(6, 0, [self.user_2.id])],
            'ks_cancel_pm2_ids': [(6, 0, [self.user_3.id])],
            'ks_edit_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_edit_pm2_ids': [(6, 0, [self.user_3.id])],
        })
        
        all_pms = config.get_all_pm_users()
        
        self.assertIn(self.user_1, all_pms)
        self.assertIn(self.user_2, all_pms)
        self.assertIn(self.user_3, all_pms)

    def test_05_get_confirm_pms_returns_correct_users(self):
        """POSITIVE: get_confirm_pms() returns correct confirmation PM users"""
        config = self.env['ks.sale.approval.config'].create({
            'company_id': self.company.id,
            'ks_approval_mode': 'dual',
            'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_confirm_pm2_ids': [(6, 0, [self.user_2.id])],
            'ks_cancel_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_cancel_pm2_ids': [(6, 0, [self.user_2.id])],
            'ks_edit_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_edit_pm2_ids': [(6, 0, [self.user_2.id])],
        })
        
        confirm_pms = config.get_confirm_pms()
        
        self.assertIn(self.user_1, confirm_pms)
        self.assertIn(self.user_2, confirm_pms)
        self.assertEqual(len(confirm_pms), 2)

    def test_06_config_can_have_overlapping_users(self):
        """POSITIVE: Same user can be in PM1 and PM2 lists (allowed at config level)"""
        config = self.env['ks.sale.approval.config'].create({
            'company_id': self.company.id,
            'ks_approval_mode': 'dual',
            'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id, self.user_2.id])],
            'ks_confirm_pm2_ids': [(6, 0, [self.user_2.id, self.user_3.id])],  # user_2 overlaps
            'ks_cancel_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_cancel_pm2_ids': [(6, 0, [self.user_2.id])],
            'ks_edit_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_edit_pm2_ids': [(6, 0, [self.user_2.id])],
        })
        
        self.assertTrue(config.id, "Configuration should be created with overlapping users")

    # ==================== NEGATIVE TEST CASES ====================

    def test_07_dual_approval_requires_pm2_for_confirmation(self):
        """NEGATIVE: Dual approval mode requires PM2 for confirmation"""
        with self.assertRaises(ValidationError):
            self.env['ks.sale.approval.config'].create({
                'company_id': self.company.id,
                'ks_approval_mode': 'dual',
                'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id])],
                'ks_confirm_pm2_ids': [(6, 0, [])],  # Missing PM2
                'ks_cancel_pm1_ids': [(6, 0, [self.user_1.id])],
                'ks_cancel_pm2_ids': [(6, 0, [self.user_2.id])],
                'ks_edit_pm1_ids': [(6, 0, [self.user_1.id])],
                'ks_edit_pm2_ids': [(6, 0, [self.user_2.id])],
            })

    def test_08_dual_approval_requires_pm2_for_cancel(self):
        """NEGATIVE: Dual approval mode requires PM2 for cancel"""
        with self.assertRaises(ValidationError):
            self.env['ks.sale.approval.config'].create({
                'company_id': self.company.id,
                'ks_approval_mode': 'dual',
                'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id])],
                'ks_confirm_pm2_ids': [(6, 0, [self.user_2.id])],
                'ks_cancel_pm1_ids': [(6, 0, [self.user_1.id])],
                'ks_cancel_pm2_ids': [(6, 0, [])],  # Missing PM2
                'ks_edit_pm1_ids': [(6, 0, [self.user_1.id])],
                'ks_edit_pm2_ids': [(6, 0, [self.user_2.id])],
            })

    def test_09_dual_approval_requires_pm2_for_edit(self):
        """NEGATIVE: Dual approval mode requires PM2 for edit"""
        with self.assertRaises(ValidationError):
            self.env['ks.sale.approval.config'].create({
                'company_id': self.company.id,
                'ks_approval_mode': 'dual',
                'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id])],
                'ks_confirm_pm2_ids': [(6, 0, [self.user_2.id])],
                'ks_cancel_pm1_ids': [(6, 0, [self.user_1.id])],
                'ks_cancel_pm2_ids': [(6, 0, [self.user_2.id])],
                'ks_edit_pm1_ids': [(6, 0, [self.user_1.id])],
                'ks_edit_pm2_ids': [(6, 0, [])],  # Missing PM2
            })

    def test_10_unique_company_constraint(self):
        """NEGATIVE: Only one configuration per company is allowed"""
        self.env['ks.sale.approval.config'].create({
            'company_id': self.company.id,
            'ks_approval_mode': 'single',
            'ks_confirm_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_cancel_pm1_ids': [(6, 0, [self.user_1.id])],
            'ks_edit_pm1_ids': [(6, 0, [self.user_1.id])],
        })
        
        with self.assertRaises(Exception):  # IntegrityError or ValidationError
            self.env['ks.sale.approval.config'].create({
                'company_id': self.company.id,
                'ks_approval_mode': 'single',
                'ks_confirm_pm1_ids': [(6, 0, [self.user_2.id])],
                'ks_cancel_pm1_ids': [(6, 0, [self.user_2.id])],
                'ks_edit_pm1_ids': [(6, 0, [self.user_2.id])],
            })

