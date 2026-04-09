# -*- coding: utf-8 -*-

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        """Validate the picking first (delivery is never blocked), then notify the
        insurance team if any related policy has reached its tolerance threshold."""
        res = super()._action_done()
        # Run in a savepoint so that any error in the insurance check never rolls back
        # the completed delivery — the notification is informational only.
        try:
            self._trigger_insurance_tolerance_check()
        except Exception:
            _logger.exception(
                "Insurance tolerance check failed after validating picking(s) %s — "
                "delivery is unaffected.", self.ids
            )
        return res

    def _trigger_insurance_tolerance_check(self):
        """Find and evaluate tolerance for every active insurance policy whose covered
        warehouse was involved in the validated pickings.

        - Marine policies: triggered by outgoing deliveries from the covered warehouse.
        - Fire & Burglary policies: triggered by any picking (incoming or outgoing) because
          both receipts and deliveries change the inventory level and therefore the balance.
        """
        warehouse_ids = self.mapped('picking_type_id.warehouse_id').ids
        if not warehouse_ids:
            return

        InsurancePolicy = self.env['insurance.policy']

        # ── Marine: only outgoing pickings from the covered warehouse matter ────────────
        outgoing_warehouse_ids = self.filtered(
            lambda p: p.picking_type_code == 'outgoing'
        ).mapped('picking_type_id.warehouse_id').ids

        if outgoing_warehouse_ids:
            marine_policies = InsurancePolicy.search([
                ('state', '=', 'active'),
                ('is_marine', '=', True),
                ('warehouse_id', 'in', outgoing_warehouse_ids),
                ('tolerance_percent', '>', 0),
            ])
            marine_policies.action_check_tolerance()

        # ── Fire & Burglary: any picking at the covered warehouse changes inventory ────
        # Individual policies: warehouse_id must match one of the picking warehouses.
        # Floater policies: at least one covered location must match.
        fb_individual = InsurancePolicy.search([
            ('state', '=', 'active'),
            ('is_fire_burglary', '=', True),
            ('policy_type', '=', 'individual'),
            ('warehouse_id', 'in', warehouse_ids),
            ('tolerance_percent', '>', 0),
        ])
        fb_floater = InsurancePolicy.search([
            ('state', '=', 'active'),
            ('is_fire_burglary', '=', True),
            ('policy_type', '=', 'floater'),
            ('floater_location_ids', 'in', warehouse_ids),
            ('tolerance_percent', '>', 0),
        ])
        (fb_individual | fb_floater).action_check_tolerance()
