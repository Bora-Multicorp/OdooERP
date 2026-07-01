# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestKsPurchaseApprovalConfig(TransactionCase):
    """Test cases for Approval Configuration Model"""

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

    def test_01_create_config_with_different_pm_users(self):
        """POSITIVE: Create configuration with different PM1 and PM2 users"""
        config = self.env['ks.purchase.approval.config'].create({
            'company_id': self.company.id,
            'ks_confirm_pm1_id': self.user_1.id,
            'ks_confirm_pm2_id': self.user_2.id,
            'ks_update_pm1_id': self.user_1.id,
            'ks_update_pm2_id': self.user_2.id,
            'ks_cancel_pm1_id': self.user_1.id,
            'ks_cancel_pm2_id': self.user_2.id,
        })
        
        self.assertTrue(config.id, "Configuration should be created successfully")
        self.assertEqual(config.ks_confirm_pm1_id, self.user_1)
        self.assertEqual(config.ks_confirm_pm2_id, self.user_2)

    def test_02_get_config_returns_correct_company_config(self):
        """POSITIVE: get_config() returns the correct company configuration"""
        config = self.env['ks.purchase.approval.config'].create({
            'company_id': self.company.id,
            'ks_confirm_pm1_id': self.user_1.id,
            'ks_confirm_pm2_id': self.user_2.id,
            'ks_update_pm1_id': self.user_1.id,
            'ks_update_pm2_id': self.user_2.id,
            'ks_cancel_pm1_id': self.user_1.id,
            'ks_cancel_pm2_id': self.user_2.id,
        })
        
        retrieved_config = self.env['ks.purchase.approval.config'].get_config(self.company.id)
        
        self.assertEqual(config.id, retrieved_config.id, "Should retrieve the same configuration")

    def test_03_get_all_pm_users_returns_all_configured_pms(self):
        """POSITIVE: get_all_pm_users() returns all PM users"""
        config = self.env['ks.purchase.approval.config'].create({
            'company_id': self.company.id,
            'ks_confirm_pm1_id': self.user_1.id,
            'ks_confirm_pm2_id': self.user_2.id,
            'ks_update_pm1_id': self.user_1.id,
            'ks_update_pm2_id': self.user_3.id,
            'ks_cancel_pm1_id': self.user_2.id,
            'ks_cancel_pm2_id': self.user_3.id,
        })
        
        all_pms = config.get_all_pm_users()
        
        self.assertIn(self.user_1, all_pms)
        self.assertIn(self.user_2, all_pms)
        self.assertIn(self.user_3, all_pms)

    def test_04_config_can_have_same_user_for_different_workflows(self):
        """POSITIVE: Same user can be PM for different workflows"""
        config = self.env['ks.purchase.approval.config'].create({
            'company_id': self.company.id,
            'ks_confirm_pm1_id': self.user_1.id,
            'ks_confirm_pm2_id': self.user_2.id,
            'ks_update_pm1_id': self.user_1.id,  # Same as confirm PM1
            'ks_update_pm2_id': self.user_2.id,  # Same as confirm PM2
            'ks_cancel_pm1_id': self.user_1.id,  # Same as confirm PM1
            'ks_cancel_pm2_id': self.user_2.id,  # Same as confirm PM2
        })
        
        self.assertTrue(config.id, "Configuration should be created with same users for different workflows")

    def test_05_config_active_field_default_true(self):
        """POSITIVE: Active field defaults to True"""
        config = self.env['ks.purchase.approval.config'].create({
            'company_id': self.company.id,
            'ks_confirm_pm1_id': self.user_1.id,
            'ks_confirm_pm2_id': self.user_2.id,
            'ks_update_pm1_id': self.user_1.id,
            'ks_update_pm2_id': self.user_2.id,
            'ks_cancel_pm1_id': self.user_1.id,
            'ks_cancel_pm2_id': self.user_2.id,
        })
        
        self.assertTrue(config.active, "Active should be True by default")

    # ==================== NEGATIVE TEST CASES ====================

    def test_06_cannot_create_config_with_same_confirm_pm1_pm2(self):
        """NEGATIVE: Cannot create configuration with same PM1 and PM2 for confirmation"""
        with self.assertRaises(ValidationError):
            self.env['ks.purchase.approval.config'].create({
                'company_id': self.company.id,
                'ks_confirm_pm1_id': self.user_1.id,
                'ks_confirm_pm2_id': self.user_1.id,  # Same as PM1
                'ks_update_pm1_id': self.user_1.id,
                'ks_update_pm2_id': self.user_2.id,
                'ks_cancel_pm1_id': self.user_1.id,
                'ks_cancel_pm2_id': self.user_2.id,
            })

    def test_07_cannot_create_config_with_same_update_pm1_pm2(self):
        """NEGATIVE: Cannot create configuration with same PM1 and PM2 for update"""
        with self.assertRaises(ValidationError):
            self.env['ks.purchase.approval.config'].create({
                'company_id': self.company.id,
                'ks_confirm_pm1_id': self.user_1.id,
                'ks_confirm_pm2_id': self.user_2.id,
                'ks_update_pm1_id': self.user_1.id,
                'ks_update_pm2_id': self.user_1.id,  # Same as PM1
                'ks_cancel_pm1_id': self.user_1.id,
                'ks_cancel_pm2_id': self.user_2.id,
            })

    def test_08_cannot_create_config_with_same_cancel_pm1_pm2(self):
        """NEGATIVE: Cannot create configuration with same PM1 and PM2 for cancel"""
        with self.assertRaises(ValidationError):
            self.env['ks.purchase.approval.config'].create({
                'company_id': self.company.id,
                'ks_confirm_pm1_id': self.user_1.id,
                'ks_confirm_pm2_id': self.user_2.id,
                'ks_update_pm1_id': self.user_1.id,
                'ks_update_pm2_id': self.user_2.id,
                'ks_cancel_pm1_id': self.user_1.id,
                'ks_cancel_pm2_id': self.user_1.id,  # Same as PM1
            })

    def test_09_cannot_create_duplicate_config_for_same_company(self):
        """NEGATIVE: Cannot create duplicate configuration for same company"""
        self.env['ks.purchase.approval.config'].create({
            'company_id': self.company.id,
            'ks_confirm_pm1_id': self.user_1.id,
            'ks_confirm_pm2_id': self.user_2.id,
            'ks_update_pm1_id': self.user_1.id,
            'ks_update_pm2_id': self.user_2.id,
            'ks_cancel_pm1_id': self.user_1.id,
            'ks_cancel_pm2_id': self.user_2.id,
        })
        
        with self.assertRaises(Exception):  # Should raise IntegrityError or similar
            self.env['ks.purchase.approval.config'].create({
                'company_id': self.company.id,  # Same company
                'ks_confirm_pm1_id': self.user_2.id,
                'ks_confirm_pm2_id': self.user_3.id,
                'ks_update_pm1_id': self.user_2.id,
                'ks_update_pm2_id': self.user_3.id,
                'ks_cancel_pm1_id': self.user_2.id,
                'ks_cancel_pm2_id': self.user_3.id,
            })

    def test_10_get_config_returns_empty_for_unconfigured_company(self):
        """NEGATIVE: get_config() returns empty for company without configuration"""
        new_company = self.env['res.company'].create({
            'name': 'Unconfigured Company',
        })
        
        config = self.env['ks.purchase.approval.config'].get_config(new_company.id)
        
        self.assertFalse(config, "Should return empty recordset for unconfigured company")



