# -*- coding: utf-8 -*-

from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _sb_tracker_sync_from_invoice(self):
        """Create or update sb.tracker for this invoice (out_invoice only)."""
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            if not move.partner_id:
                continue
            tracker_model = self.env['sb.tracker']
            tracker = tracker_model.search([('invoice_id', '=', move.id)], limit=1)
            bank_id = getattr(move, 'ks_bank_id', None)
            ad_code = bank_id and getattr(bank_id, 'bank_ad_code', None) or ''
            if tracker:
                tracker._update_from_invoice(move)
            else:
                vals = {
                    'partner_id': move.partner_id.id,
                    'document_type': 'Sales Invoice',
                    'invoice_id': move.id,
                    'invoice_date': move.invoice_date,
                    'forex_amount': move.amount_total or 0.0,
                    'bank_id': bank_id.id if bank_id else False,
                    'ad_code': ad_code or '',
                }
                tracker_model.create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        out_invoices = moves.filtered(
            lambda m: m.move_type == 'out_invoice' and m.partner_id
        )
        if out_invoices:
            out_invoices._sb_tracker_sync_from_invoice()
        return moves

    def write(self, vals):
        res = super().write(vals)
        to_sync = self.filtered(
            lambda m: m.move_type == 'out_invoice' and m.partner_id
        )
        if to_sync:
            to_sync._sb_tracker_sync_from_invoice()
        return res
