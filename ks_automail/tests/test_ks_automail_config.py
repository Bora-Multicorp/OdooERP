# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from .common import KsAutomailCommon


class TestKsAutomailConfig(KsAutomailCommon):
    """Test cases for Auto Mail Configuration"""

    def test_01_create_automail_config(self):
        """Test: Create auto mail configuration"""
        config = self.env['ks.automail.config'].create({
            'name': 'India Email Config',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
            'auto_send_confirmation': True,
            'auto_send_packed': True,
            'auto_send_shipped': True,
        })
        
        self.assertEqual(config.zone, 'india')
        self.assertEqual(config.company_id, self.company)

    def test_02_get_config_for_order_company_specific(self):
        """Test: get_config_for_order returns company-specific config"""
        config = self.env['ks.automail.config'].create({
            'name': 'India Company Config',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
        })
        
        retrieved_config = self.env['ks.automail.config'].get_config_for_order(
            'india', self.company.id
        )
        
        self.assertEqual(retrieved_config.id, config.id, "Should retrieve company-specific config")

    def test_03_get_config_for_order_global_fallback(self):
        """Test: get_config_for_order falls back to global config"""
        # Create global config (no company)
        global_config = self.env['ks.automail.config'].create({
            'name': 'India Global Config',
            'zone': 'india',
            'company_id': False,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
        })
        
        # Create another company
        company_2 = self.env['res.company'].create({
            'name': 'Test Company 2',
        })
        
        retrieved_config = self.env['ks.automail.config'].get_config_for_order(
            'india', company_2.id
        )
        
        self.assertEqual(retrieved_config.id, global_config.id, "Should fall back to global config")

    def test_04_unique_config_per_zone_company(self):
        """Test: Only one active config per zone/company combination"""
        self.env['ks.automail.config'].create({
            'name': 'India Config 1',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
            'active': True,
        })
        
        with self.assertRaises(ValidationError):
            self.env['ks.automail.config'].create({
                'name': 'India Config 2',
                'zone': 'india',
                'company_id': self.company.id,
                'email_template_confirmation_id': self.confirmation_template.id,
                'email_template_packed_id': self.packed_template.id,
                'email_template_shipped_id': self.shipped_template.id,
                'active': True,
            })

    def test_05_multiple_configs_different_zones(self):
        """Test: Multiple configs allowed for different zones"""
        config_india = self.env['ks.automail.config'].create({
            'name': 'India Config',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
        })
        
        config_dubai = self.env['ks.automail.config'].create({
            'name': 'Dubai Config',
            'zone': 'dubai',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
        })
        
        self.assertEqual(config_india.zone, 'india')
        self.assertEqual(config_dubai.zone, 'dubai')

    def test_06_toggle_active(self):
        """Test: Toggle active status"""
        config = self.env['ks.automail.config'].create({
            'name': 'Test Config',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
            'active': True,
        })
        
        config.toggle_active()
        self.assertFalse(config.active, "Active should be toggled to False")
        
        config.toggle_active()
        self.assertTrue(config.active, "Active should be toggled back to True")

    def test_07_default_recipients(self):
        """Test: Default recipients are stored"""
        config = self.env['ks.automail.config'].create({
            'name': 'Test Config',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
            'default_recipient_ids': [(6, 0, [self.recipient.id])],
        })
        
        self.assertIn(self.recipient, config.default_recipient_ids)

