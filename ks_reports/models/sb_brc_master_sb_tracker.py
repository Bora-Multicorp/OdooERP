# -*- coding: utf-8 -*-

from odoo import api, models


class SbBrcMaster(models.Model):
    _inherit = 'sb.brc.master'

    def _sb_tracker_sync_from_master(self):
        """Create or update sb.tracker from this sb.brc.master (by invoice_id)."""
        for master in self:
            if not master.invoice_id:
                continue
            tracker_model = self.env['sb.tracker']
            tracker = tracker_model.search([
                ('invoice_id', '=', master.invoice_id.id),
            ], limit=1)
            if tracker:
                tracker._update_from_sb_brc_master(master)
            else:
                inv = master.invoice_id
                bank_id = getattr(inv, 'ks_bank_id', None)
                ad_code = bank_id and getattr(bank_id, 'bank_ad_code', None) or ''
                vals = {
                    'partner_id': inv.partner_id.id,
                    'document_type': 'Sales Invoice',
                    'invoice_id': inv.id,
                    'invoice_date': inv.invoice_date,
                    'forex_amount': inv.amount_total or 0.0,
                    'shipping_no': master.sb_no or '',
                    'shipping_date': master.sb_date,
                    'exchange_rate': master.sb_ex_rate or master.ex_rate or 0.0,
                    'inr_amount': master.amount_inr or 0.0,
                    'brc_date': master.brc_date,
                    'brc_no': master.brc_no or '',
                    'brc_amount': master.brc_amount_usd or 0.0,
                    'bank_id': bank_id.id if bank_id else False,
                    'ad_code': ad_code or '',
                }
                tracker_model.create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        masters = super().create(vals_list)
        with_invoice = masters.filtered(lambda m: m.invoice_id)
        if with_invoice:
            with_invoice._sb_tracker_sync_from_master()
        return masters

    def write(self, vals):
        res = super().write(vals)
        to_sync = self.filtered(lambda m: m.invoice_id)
        if to_sync:
            to_sync._sb_tracker_sync_from_master()
        return res
