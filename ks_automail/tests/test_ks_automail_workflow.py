# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from .common import KsAutomailCommon


class TestKsAutomailWorkflow(KsAutomailCommon):
    """Test cases for Auto Mail Workflow"""

    def test_01_confirmation_email_sent_for_india(self):
        """Test: Confirmation email sent for India zone"""
        config = self.env['ks.automail.config'].create({
            'name': 'India Config',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
            'auto_send_confirmation': True,
            'default_recipient_ids': [(6, 0, [self.recipient.id])],
        })
        
        order = self.sale_order
        order.ks_zone = 'india'
        order.ks_email_recipient_ids = [(6, 0, [self.recipient.id])]
        
        # Confirm order
        order.action_confirm()
        
        # Check that email was marked as sent
        self.assertTrue(order.ks_email_confirmed_sent, "Confirmation email should be sent")

    def test_02_no_email_for_russia_zone(self):
        """Test: No automatic email sent for Russia zone"""
        order = self.sale_order
        order.ks_zone = 'russia'
        
        # Confirm order
        order.action_confirm()
        
        # Check that email was not sent
        self.assertFalse(order.ks_email_confirmed_sent, "No email should be sent for Russia zone")

    def test_03_auto_send_settings_from_config(self):
        """Test: Auto-send settings computed from config"""
        config = self.env['ks.automail.config'].create({
            'name': 'India Config',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
            'auto_send_confirmation': False,
            'auto_send_packed': True,
            'auto_send_shipped': False,
        })
        
        order = self.sale_order
        order.ks_zone = 'india'
        order._compute_auto_send_settings()
        
        self.assertFalse(order.ks_auto_send_confirmation, "Should use config setting")
        self.assertTrue(order.ks_auto_send_packed, "Should use config setting")
        self.assertFalse(order.ks_auto_send_shipped, "Should use config setting")

    def test_04_get_email_recipients_from_order(self):
        """Test: Email recipients retrieved from order"""
        order = self.sale_order
        order.ks_email_recipient_ids = [(6, 0, [self.recipient.id])]
        
        email_to, email_cc = order._get_email_recipients()
        
        self.assertIn(self.recipient.email, email_to)

    def test_05_get_email_recipients_from_config(self):
        """Test: Email recipients fall back to config"""
        config = self.env['ks.automail.config'].create({
            'name': 'India Config',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
            'default_recipient_ids': [(6, 0, [self.recipient.id])],
        })
        
        order = self.sale_order
        order.ks_zone = 'india'
        # No order-specific recipients
        
        email_to, email_cc = order._get_email_recipients()
        
        self.assertIn(self.recipient.email, email_to, "Should use config recipients")

    def test_06_get_email_recipients_fallback_to_customer(self):
        """Test: Email recipients fall back to customer"""
        order = self.sale_order
        order.ks_zone = 'india'
        # No order recipients, no config
        
        email_to, email_cc = order._get_email_recipients()
        
        self.assertIn(self.customer.email, email_to, "Should fall back to customer email")

    def test_07_manual_email_send(self):
        """Test: Manual email send works for any zone"""
        order = self.sale_order
        order.ks_zone = 'russia'  # Russia doesn't get auto emails
        order.ks_email_recipient_ids = [(6, 0, [self.recipient.id])]
        
        # Manual send should work
        result = order.action_send_manual_email('confirmation')
        
        self.assertEqual(result['type'], 'ir.actions.client')

    def test_08_compute_automail_config_id(self):
        """Test: Automail config ID is computed from zone and company"""
        config = self.env['ks.automail.config'].create({
            'name': 'India Config',
            'zone': 'india',
            'company_id': self.company.id,
            'email_template_confirmation_id': self.confirmation_template.id,
            'email_template_packed_id': self.packed_template.id,
            'email_template_shipped_id': self.shipped_template.id,
        })
        
        order = self.sale_order
        order.ks_zone = 'india'
        order._compute_ks_automail_config_id()
        
        self.assertEqual(order.ks_automail_config_id.id, config.id)

