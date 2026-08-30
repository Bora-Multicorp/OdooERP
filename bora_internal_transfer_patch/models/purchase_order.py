# -*- coding: utf-8 -*-

from odoo import models, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def _requires_approval(self):
        """True if this PO must go through approval workflow.
        Bypasses approval workflow (returns False) for:
        - E-commerce imported POs (ks_ecom_imported = True)
        - Inter-company transfer POs (auto_generated = True, auto_sale_order_id present, or inter_company context)
        """
        self.ensure_one()
        if getattr(self, 'ks_ecom_imported', False):
            return False
        if getattr(self, 'auto_generated', False) or getattr(self, 'auto_sale_order_id', False):
            return False
        if self.env.context.get('inter_company_create_object') or self.env.context.get('auto_purchase_order_id') or self.env.context.get('auto_sale_order_id'):
            return False
        return super()._requires_approval()
