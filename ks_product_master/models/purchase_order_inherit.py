# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    made_country = fields.Many2one(
        'res.country',
        string='Made In',
        help="Country where this line's product is manufactured.",
        tracking=True,
    )


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        """After confirmation, auto-populate made_country on the generated receipt
        picking when all PO lines share the same Made In country."""
        res = super().button_confirm()
        for order in self:
            order._sync_made_country_to_receipt()
        return res

    def _sync_made_country_to_receipt(self):
        """Sync made_country from PO lines to the receipt picking.

        Rules:
        - All lines share the same country → set made_country on the picking header
          and cascade to every move / move line.
        - Lines differ → push the per-line country down to the matching stock.move
          and its move lines; the user manages the picking header manually.
        """
        self.ensure_one()

        lines_with_country = self.order_line.filtered(lambda l: l.made_country)
        if not lines_with_country:
            return

        receipts = self.picking_ids.filtered(
            lambda p: p.picking_type_id.code == 'incoming'
            and p.state not in ('done', 'cancel')
        )
        if not receipts:
            return

        unique_country_ids = set(lines_with_country.mapped('made_country').ids)

        if len(unique_country_ids) == 1:
            # All lines agree — stamp the header and cascade.
            single_country_id = list(unique_country_ids)[0]
            for receipt in receipts:
                receipt.write({'made_country': single_country_id})
                receipt.move_ids.write({'made_country': single_country_id})
                receipt.move_line_ids.write({'made_country': single_country_id})
        else:
            # Mixed countries — propagate per purchase line to the matching move.
            for receipt in receipts:
                for move in receipt.move_ids:
                    po_line = move.purchase_line_id
                    if po_line and po_line.made_country:
                        move.write({'made_country': po_line.made_country.id})
                        move.move_line_ids.write({'made_country': po_line.made_country.id})
