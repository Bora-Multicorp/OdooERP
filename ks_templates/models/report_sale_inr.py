# -*- coding: utf-8 -*-
from odoo import models


class ReportSaleOrderINR(models.AbstractModel):
    _name = 'report.ks_templates.report_saleorder_dubai_inr'

    def _get_report_values(self, docids, data=None):
        docs = self.env['sale.order'].browse(docids)
        inr_rates = {}
        for doc in docs:
            inr_rates[doc.id] = doc.get_inr_conversion_info()
        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': docs,
            'inr_rates': inr_rates,
        }
