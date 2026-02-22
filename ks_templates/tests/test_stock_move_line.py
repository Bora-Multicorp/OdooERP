# -*- coding: utf-8 -*-
"""Test cases for stock.move.line model extensions in ks_templates"""

from .common import KsTemplatesCommon


class TestStockMoveLine(KsTemplatesCommon):
    """Test cases for stock.move.line model"""

    def test_ks_no_kin_of_pkg_field(self):
        """Test ks_no_kin_of_pkg field"""
        self.stock_move_line.ks_no_kin_of_pkg = '10 BOXES (1-10)'
        self.assertEqual(self.stock_move_line.ks_no_kin_of_pkg, '10 BOXES (1-10)')

    def test_ks_remark_field(self):
        """Test ks_remark field"""
        self.stock_move_line.ks_remark = 'Handle with care'
        self.assertEqual(self.stock_move_line.ks_remark, 'Handle with care')

    def test_ks_remark_multiline(self):
        """Test ks_remark field with multiline text"""
        multiline_text = 'First line\nSecond line\nThird line'
        self.stock_move_line.ks_remark = multiline_text
        self.assertEqual(self.stock_move_line.ks_remark, multiline_text)

    def test_fields_accessible(self):
        """Test that both fields are accessible and can be set"""
        self.stock_move_line.write({
            'ks_no_kin_of_pkg': '5 BOXES',
            'ks_remark': 'Test remark',
        })
        
        self.assertEqual(self.stock_move_line.ks_no_kin_of_pkg, '5 BOXES')
        self.assertEqual(self.stock_move_line.ks_remark, 'Test remark')

