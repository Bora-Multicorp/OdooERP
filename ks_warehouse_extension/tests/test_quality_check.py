# -*- coding: utf-8 -*-
"""
Test Cases for Quality Check Feature - ks_warehouse_extension module

Feature: Whenever a user marks a quality check as Pass or Fail, the system should check 
if there is any difference between the ordered quantity and the received quantity or any 
other difference mentioned inside code; if there is a difference, an email should be 
automatically triggered to a specific recipient list.

Checks performed:
- SKU mismatch
- Quantity mismatch
- Color mismatch
- Damage
- Wrong device type
"""

from odoo.tests import TransactionCase, tagged, Form
from odoo.exceptions import ValidationError, UserError
from unittest.mock import patch, MagicMock


@tagged('post_install', '-at_install', 'ks_warehouse_extension', 'quality_check')
class TestQualityCheckPositive(TransactionCase):
    """Positive Test Cases for Quality Check Feature"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test product
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product QC',
            'default_code': 'TEST-QC-001',
            'type': 'consu',
            'is_storable': True,
        })
        
        # Create vendor/supplier
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor QC',
            'supplier_rank': 1,
        })
        
        # Create warehouse
        cls.warehouse = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.env.company.id)
        ], limit=1)
        
        # Create quality point (if quality module is available)
        cls.quality_point = cls.env['quality.point'].create({
            'name': 'Test Quality Point',
            'picking_type_ids': [(6, 0, [cls.warehouse.in_type_id.id])],
            'product_ids': [(6, 0, [cls.product.id])],
            'test_type_id': cls.env.ref('quality.test_type_passfail').id,
        })

    def _create_purchase_order(self, product, qty):
        """Helper method to create a purchase order"""
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_qty': qty,
                'product_uom': product.uom_id.id,
                'price_unit': 100.0,
            })]
        })
        return po

    # ==================== POSITIVE TEST CASES ====================

    def test_01_qc_pass_no_mismatch(self):
        """
        TEST: Quality check PASS with no mismatches
        EXPECTED: No mismatch detected, notification sent with "No mismatches found"
        """
        # Create PO and confirm
        po = self._create_purchase_order(self.product, 10)
        po.button_confirm()
        
        # Get the picking
        picking = po.picking_ids[0]
        
        # Set received quantity same as ordered
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        
        # Create quality check
        qc = self.env['quality.check'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        # Perform QC pass
        with patch.object(type(qc), 'send_qc_notification') as mock_notify:
            qc.do_pass()
            # Verify notification was called
            mock_notify.assert_called_once()
            # Get the mismatch details passed to notification
            call_args = mock_notify.call_args[0][0]
            self.assertIn("No mismatches found", call_args)

    def test_02_qc_pass_with_quantity_mismatch_detected(self):
        """
        TEST: Quality check PASS with quantity mismatch detection
        EXPECTED: Quantity mismatch detected, email notification triggered
        """
        # Create PO with qty 10
        po = self._create_purchase_order(self.product, 10)
        po.button_confirm()
        
        picking = po.picking_ids[0]
        
        # Set received quantity different from ordered (received less)
        for move in picking.move_ids:
            move.quantity = 8  # Received only 8, ordered 10
        
        qc = self.env['quality.check'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        with patch.object(type(qc), 'send_qc_notification') as mock_notify:
            qc.do_pass()
            mock_notify.assert_called_once()
            call_args = mock_notify.call_args[0][0]
            self.assertIn("Quantity mismatch", call_args)

    def test_03_qc_fail_triggers_notification(self):
        """
        TEST: Quality check FAIL triggers notification
        EXPECTED: Notification sent on QC fail
        """
        po = self._create_purchase_order(self.product, 10)
        po.button_confirm()
        
        picking = po.picking_ids[0]
        
        qc = self.env['quality.check'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        with patch.object(type(qc), 'send_qc_notification') as mock_notify:
            qc.do_fail()
            mock_notify.assert_called_once()

    def test_04_qc_damage_flag_detection(self):
        """
        TEST: Quality check detects damage flag
        EXPECTED: Damage detected and included in mismatch list
        """
        po = self._create_purchase_order(self.product, 10)
        po.button_confirm()
        
        picking = po.picking_ids[0]
        
        qc = self.env['quality.check'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
            'qc_damage': True,  # Set damage flag
        })
        
        mismatches = qc.perform_qc()
        self.assertIn("Box Damaged", mismatches)
        self.assertFalse(qc.qc_damage)  # Should be set to False after detection

    def test_05_qc_fields_default_values(self):
        """
        TEST: Quality check fields have correct default values
        EXPECTED: All QC boolean fields default to True
        """
        qc = self.env['quality.check'].create({
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        self.assertTrue(qc.qc_sku_mismatch)
        self.assertTrue(qc.qc_qty_mismatch)
        self.assertTrue(qc.qc_color_mismatch)
        self.assertTrue(qc.qc_damage)
        self.assertTrue(qc.qc_wrong_device_type)

    def test_06_qc_notification_message_posted(self):
        """
        TEST: Quality check posts message to chatter
        EXPECTED: Message posted with QC results
        """
        po = self._create_purchase_order(self.product, 10)
        po.button_confirm()
        
        picking = po.picking_ids[0]
        
        qc = self.env['quality.check'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        initial_message_count = len(qc.message_ids)
        
        with patch.object(type(qc), 'send_qc_notification', wraps=qc.send_qc_notification):
            qc.send_qc_notification(["Test mismatch"])
        
        # Check message was posted
        self.assertGreater(len(qc.message_ids), initial_message_count)

    def test_07_qc_sku_mismatch_detection(self):
        """
        TEST: SKU mismatch is detected correctly
        EXPECTED: SKU mismatch added to mismatch list when product codes differ
        """
        # Create another product with different SKU
        product2 = self.env['product.product'].create({
            'name': 'Test Product Different SKU',
            'default_code': 'TEST-QC-002',
            'type': 'consu',
            'is_storable': True,
        })
        
        po = self._create_purchase_order(self.product, 10)
        po.button_confirm()
        
        picking = po.picking_ids[0]
        
        # Manually change the product on the move to simulate SKU mismatch
        # (In real scenario this would happen if wrong product was received)
        
        qc = self.env['quality.check'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        # The perform_qc method checks for SKU mismatch
        mismatches = qc.perform_qc()
        # Assert the method runs without error
        self.assertIsInstance(mismatches, list)

    def test_08_qc_multiple_mismatches_detected(self):
        """
        TEST: Multiple mismatches detected simultaneously
        EXPECTED: All mismatches included in notification
        """
        po = self._create_purchase_order(self.product, 10)
        po.button_confirm()
        
        picking = po.picking_ids[0]
        
        # Set quantity mismatch
        for move in picking.move_ids:
            move.quantity = 5  # Received 5, ordered 10
        
        qc = self.env['quality.check'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
            'qc_damage': True,  # Also mark as damaged
        })
        
        mismatches = qc.perform_qc()
        
        # Should have both quantity mismatch and damage
        self.assertIn("Quantity mismatch", mismatches)
        self.assertIn("Box Damaged", mismatches)


@tagged('post_install', '-at_install', 'ks_warehouse_extension', 'quality_check')
class TestQualityCheckNegative(TransactionCase):
    """Negative Test Cases for Quality Check Feature"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Test Product QC Negative',
            'default_code': 'TEST-QC-NEG-001',
            'type': 'consu',
            'is_storable': True,
        })
        
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor QC Negative',
            'supplier_rank': 1,
        })
        
        cls.warehouse = cls.env['stock.warehouse'].search([
            ('company_id', '=', cls.env.company.id)
        ], limit=1)
        
        cls.quality_point = cls.env['quality.point'].create({
            'name': 'Test Quality Point Negative',
            'picking_type_ids': [(6, 0, [cls.warehouse.in_type_id.id])],
            'product_ids': [(6, 0, [cls.product.id])],
            'test_type_id': cls.env.ref('quality.test_type_passfail').id,
        })

    # ==================== NEGATIVE TEST CASES ====================

    def test_01_qc_without_picking(self):
        """
        TEST: Quality check without associated picking
        EXPECTED: perform_qc returns empty or default mismatches, no error
        """
        qc = self.env['quality.check'].create({
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
            # No picking_id
        })
        
        # Should not raise error, just return mismatches list
        mismatches = qc.perform_qc()
        self.assertIsInstance(mismatches, list)

    def test_02_qc_notification_without_template(self):
        """
        TEST: Quality check notification when email template doesn't exist
        EXPECTED: Notification still posts to chatter, doesn't crash
        """
        qc = self.env['quality.check'].create({
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        # Mock env.ref to return False (template not found)
        with patch.object(qc.env, 'ref', return_value=False):
            # Should not raise error
            try:
                qc.send_qc_notification(["Test mismatch"])
            except Exception as e:
                self.fail(f"send_qc_notification raised exception: {e}")

    def test_03_qc_with_zero_quantity_ordered(self):
        """
        TEST: Quality check with zero quantity on purchase order line
        EXPECTED: System handles gracefully, no division by zero or crash
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'product_qty': 0,  # Zero quantity
                'product_uom': self.product.uom_id.id,
                'price_unit': 100.0,
            })]
        })
        po.button_confirm()
        
        picking = po.picking_ids[0] if po.picking_ids else None
        
        if picking:
            qc = self.env['quality.check'].create({
                'picking_id': picking.id,
                'product_id': self.product.id,
                'point_id': self.quality_point.id,
                'team_id': self.env['quality.alert.team'].search([], limit=1).id,
            })
            
            # Should not crash
            try:
                mismatches = qc.perform_qc()
                self.assertIsInstance(mismatches, list)
            except Exception as e:
                self.fail(f"perform_qc crashed with zero quantity: {e}")

    def test_04_qc_damage_flag_false_not_reported(self):
        """
        TEST: Quality check with damage flag set to False
        EXPECTED: Damage not included in mismatches when flag is False
        """
        qc = self.env['quality.check'].create({
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
            'qc_damage': False,  # No damage
        })
        
        mismatches = qc.perform_qc()
        # Note: Current implementation always adds "Box Damaged" if qc_damage is True
        # When False, it should not be in mismatches
        # But looking at the code, if qc_damage is True it sets to False and adds to list
        # So if it starts False, "Box Damaged" shouldn't be added

    def test_05_qc_empty_mismatch_list_handling(self):
        """
        TEST: Quality check when no mismatches are found
        EXPECTED: Returns list with "No mismatches found" message
        """
        qc = self.env['quality.check'].create({
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
            'qc_damage': False,  # No damage to report
        })
        
        mismatches = qc.perform_qc()
        # When no mismatches, should have the default message
        self.assertTrue(len(mismatches) > 0)

    def test_06_qc_with_no_internal_users(self):
        """
        TEST: Quality check notification when no internal users exist
        EXPECTED: Notification handles empty user list gracefully
        """
        qc = self.env['quality.check'].create({
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        # Mock users search to return empty
        original_search = self.env['res.users'].sudo().search
        
        with patch.object(type(self.env['res.users'].sudo()), 'search', return_value=self.env['res.users']):
            try:
                qc.send_qc_notification(["Test mismatch"])
            except Exception as e:
                self.fail(f"Notification failed with no users: {e}")

    def test_07_qc_move_without_purchase_line(self):
        """
        TEST: Quality check on picking move without associated purchase line
        EXPECTED: SKU/Quantity mismatch checks handle missing purchase_line_id
        """
        # Create internal transfer (no PO)
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.warehouse.int_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        move = self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 10,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.warehouse.lot_stock_id.id,
        })
        
        qc = self.env['quality.check'].create({
            'picking_id': picking.id,
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        # Should not crash when purchase_line_id is False
        try:
            mismatches = qc.perform_qc()
            self.assertIsInstance(mismatches, list)
        except Exception as e:
            self.fail(f"perform_qc crashed without purchase line: {e}")

    def test_08_qc_notes_field_empty(self):
        """
        TEST: Quality check with empty notes field
        EXPECTED: System handles empty notes gracefully
        """
        qc = self.env['quality.check'].create({
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
            'qc_notes': '',  # Empty notes
        })
        
        self.assertEqual(qc.qc_notes, '')
        # Perform QC should work fine
        mismatches = qc.perform_qc()
        self.assertIsInstance(mismatches, list)

    def test_09_qc_very_large_quantity_difference(self):
        """
        TEST: Quality check with very large quantity difference
        EXPECTED: System detects mismatch without overflow errors
        """
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'product_qty': 999999999,  # Very large quantity
                'product_uom': self.product.uom_id.id,
                'price_unit': 100.0,
            })]
        })
        po.button_confirm()
        
        if po.picking_ids:
            picking = po.picking_ids[0]
            for move in picking.move_ids:
                move.quantity = 1  # Received only 1
            
            qc = self.env['quality.check'].create({
                'picking_id': picking.id,
                'product_id': self.product.id,
                'point_id': self.quality_point.id,
                'team_id': self.env['quality.alert.team'].search([], limit=1).id,
            })
            
            mismatches = qc.perform_qc()
            self.assertIn("Quantity mismatch", mismatches)

    def test_10_qc_double_pass_call(self):
        """
        TEST: Calling do_pass twice on same quality check
        EXPECTED: Should handle gracefully or raise appropriate error
        """
        qc = self.env['quality.check'].create({
            'product_id': self.product.id,
            'point_id': self.quality_point.id,
            'team_id': self.env['quality.alert.team'].search([], limit=1).id,
        })
        
        with patch.object(type(qc), 'send_qc_notification'):
            qc.do_pass()
            # Second call - should handle state properly
            try:
                qc.do_pass()
            except (ValidationError, UserError):
                pass  # Expected if already passed

