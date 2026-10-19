# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestOrderZone(TransactionCase):
    """Test suite for Sale Order and Purchase Order ks_zone default and onchange behaviors."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Find existing companies for Indian, Dubai, and Hong Kong
        cls.indian_company = cls.env['res.company'].search(
            [('partner_id.country_id.code', '=', 'IN')], limit=1
        ) or cls.env.company

        cls.dubai_company = cls.env['res.company'].search(
            [('partner_id.country_id.code', '=', 'AE')], limit=1
        )
        if not cls.dubai_company:
            cls.dubai_company = cls.env['res.company'].search(
                [('name', 'ilike', 'Ayaan Impex')], limit=1
            ) or cls.env['res.company'].search(
                [('name', 'ilike', 'Bora Electronics FZCO')], limit=1
            )

        cls.hk_company = cls.env['res.company'].search(
            [('partner_id.country_id.code', '=', 'HK')], limit=1
        )
        if not cls.hk_company:
            cls.hk_company = cls.env['res.company'].search(
                [('name', 'ilike', 'Hong Kong')], limit=1
            )

    def test_01_default_ks_zone_dubai_company(self):
        """Sale order under Dubai company defaults to 'dafza'."""
        if self.dubai_company:
            so_model = self.env['sale.order'].with_company(self.dubai_company)
            defaults = so_model.default_get(['ks_zone', 'company_id'])
            self.assertEqual(defaults.get('ks_zone'), 'dafza')

    def test_02_default_ks_zone_indian_company(self):
        """Sale order under Indian company defaults to 'india'."""
        if self.indian_company:
            so_model = self.env['sale.order'].with_company(self.indian_company)
            defaults = so_model.default_get(['ks_zone', 'company_id'])
            self.assertEqual(defaults.get('ks_zone'), 'india')

    def test_03_default_ks_zone_overseas_non_dubai_company(self):
        """Sale order under overseas non-Dubai company defaults to first option 'russia'."""
        if self.hk_company:
            so_model = self.env['sale.order'].with_company(self.hk_company)
            defaults = so_model.default_get(['ks_zone', 'company_id'])
            self.assertEqual(defaults.get('ks_zone'), 'russia')

    def test_04_onchange_company_id_transitions(self):
        """Test onchange updates ks_zone appropriately when switching companies."""
        if not (self.indian_company and self.dubai_company and self.hk_company):
            return

        order = self.env['sale.order'].new({
            'company_id': self.indian_company.id,
            'ks_zone': 'india',
        })
        self.assertEqual(order.ks_zone, 'india')

        # Switch to Dubai company -> should update to 'dafza'
        order.company_id = self.dubai_company
        order._onchange_company_id_update_zone()
        self.assertEqual(order.ks_zone, 'dafza')

        # Switch to Hong Kong company -> should update to 'russia'
        order.company_id = self.hk_company
        order._onchange_company_id_update_zone()
        self.assertEqual(order.ks_zone, 'russia')

        # Switch back to Indian company -> should update to 'india'
        order.company_id = self.indian_company
        order._onchange_company_id_update_zone()
        self.assertEqual(order.ks_zone, 'india')

    def test_05_default_ks_zone_purchase_order_dubai(self):
        """Purchase order under Dubai company defaults to 'dafza'."""
        if self.dubai_company:
            po_model = self.env['purchase.order'].with_company(self.dubai_company)
            defaults = po_model.default_get(['ks_zone', 'company_id'])
            self.assertEqual(defaults.get('ks_zone'), 'dafza')

    def test_06_default_ks_zone_purchase_order_india(self):
        """Purchase order under Indian company defaults to 'india'."""
        if self.indian_company:
            po_model = self.env['purchase.order'].with_company(self.indian_company)
            defaults = po_model.default_get(['ks_zone', 'company_id'])
            self.assertEqual(defaults.get('ks_zone'), 'india')

    def test_07_default_ks_zone_purchase_order_overseas_non_dubai(self):
        """Purchase order under overseas non-Dubai company defaults to 'russia'."""
        if self.hk_company:
            po_model = self.env['purchase.order'].with_company(self.hk_company)
            defaults = po_model.default_get(['ks_zone', 'company_id'])
            self.assertEqual(defaults.get('ks_zone'), 'russia')

    def test_08_purchase_order_onchange_company_id(self):
        """Test PO onchange updates ks_zone appropriately when switching companies."""
        if not (self.indian_company and self.dubai_company and self.hk_company):
            return

        order = self.env['purchase.order'].new({
            'company_id': self.indian_company.id,
            'ks_zone': 'india',
        })
        self.assertEqual(order.ks_zone, 'india')

        # Switch to Dubai company -> should update to 'dafza'
        order.company_id = self.dubai_company
        order._onchange_company_id_update_zone()
        self.assertEqual(order.ks_zone, 'dafza')

        # Switch to Hong Kong company -> should update to 'russia'
        order.company_id = self.hk_company
        order._onchange_company_id_update_zone()
        self.assertEqual(order.ks_zone, 'russia')

        # Switch back to Indian company -> should update to 'india'
        order.company_id = self.indian_company
        order._onchange_company_id_update_zone()
        self.assertEqual(order.ks_zone, 'india')
