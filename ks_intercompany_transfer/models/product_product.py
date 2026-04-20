# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models
from odoo.tools.float_utils import float_round

VIRTUAL_USAGES = ('inventory', 'production', 'transit')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    inter_company_transfer_qty = fields.Float(
        'Inter-Company Transfer',
        compute='_compute_inter_company_transfer_qty',
        digits='Product Unit of Measure',
        compute_sudo=True,
        help="Sum of done quantities from internal transfers whose destination "
             "is a virtual location (usage inventory/production/transit or Virtual Location flag).",
    )

    @api.depends_context('allowed_company_ids')
    def _compute_inter_company_transfer_qty(self):
        """Sum of done move quantities from internal transfers where the
        destination location is virtual: usage in ('inventory', 'production', 'transit')
        or custom field x_is_virtual is True."""
        Move = self.env['stock.move'].sudo()
        product_ids = self._origin.ids if self._origin else self.ids
        if not product_ids:
            for product in self:
                product.inter_company_transfer_qty = 0.0
            return

        domain = [
            ('product_id', 'in', product_ids),
            ('state', '=', 'assigned'),
        ]
        moves = Move.search(domain)
        # Internal transfers only: move belongs to a picking with operation type 'internal'
        internal_moves = moves.filtered(
            lambda m: m.picking_type_id and m.picking_type_id.code == 'internal'
        )
        # Destination is virtual: usage in ('inventory','production','transit') or x_is_virtual
        virtual_dest_moves = internal_moves.filtered(
            lambda m: (
                (m.location_dest_id.usage in VIRTUAL_USAGES)
                or (m.location_dest_id.x_is_virtual)
            )
        )

        sums = defaultdict(float)
        for move in virtual_dest_moves:
            qty = move.product_uom._compute_quantity(
                move.quantity,
                move.product_id.uom_id,
                rounding_method='HALF-UP',
            )
            sums[move.product_id.id] += qty

        for product in self:
            if product.type == 'service':
                product.inter_company_transfer_qty = 0.0
                continue
            origin_id = product._origin.id if product._origin else product.id
            qty = sums.get(origin_id, 0.0)
            if origin_id and product.uom_id:
                qty = float_round(qty, precision_rounding=product.uom_id.rounding)
            product.inter_company_transfer_qty = qty
