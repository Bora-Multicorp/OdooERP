# -*- coding: utf-8 -*-
from odoo import models


class ReportPurchaseOrderSavex(models.AbstractModel):
    _name = 'report.ks_templates.purchase_order_savex_report'
    _description = 'Savex Purchase Order Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': docs,
        }


class ReportPurchaseOrderWithoutDiscount(models.AbstractModel):
    _name = 'report.ks_templates.purchase_order_without_discount_report'
    _description = 'Purchase Order Domestic Without Discount Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': docs,
        }


class ReportPurchaseOrderCustom(models.AbstractModel):
    _name = 'report.ks_templates.purchase_order_custom_report'
    _description = 'Purchase Order Custom Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': docs,
        }


class ReportPurchaseOrderBase(models.AbstractModel):
    _name = 'report.purchase.report_purchaseorder'
    _description = 'Base Purchase Order Report'

    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.order'].sudo().browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': docs,
        }
