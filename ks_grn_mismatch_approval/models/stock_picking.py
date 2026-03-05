# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ks_grn_mismatch_approved = fields.Boolean(
        string='GRN Mismatch Approved',
        default=False,
        copy=False,
        help='True when a GRN mismatch approval request for this receipt has been approved.',
    )
    ks_grn_mismatch_approval_count = fields.Integer(
        string='GRN Mismatch Requests',
        compute='_compute_ks_grn_mismatch_approval_count',
    )

    def _compute_ks_grn_mismatch_approval_count(self):
        """Count GRN mismatch approval requests for this picking. Not stored; computed on read (cannot depend on 'id')."""
        for picking in self:
            picking.ks_grn_mismatch_approval_count = (
                picking.env['ks.grn.mismatch.approval'].search_count([
                    ('picking_id', '=', picking.id),
                ]) if picking.id else 0
            )

    def _ks_get_grn_mismatches(self):
        """
        For an incoming picking linked to a purchase order, detect:
        - Quantity mismatch: received qty > PO line demand for any move.
        - New product: move with no purchase_line_id (product not on PO).
        Returns list of dicts: [{'type': 'qty'|'new_product', 'message': str, 'move': record}]
        """
        self.ensure_one()
        if self.picking_type_id.code != 'incoming' or not self.purchase_id:
            return []
        mismatches = []
        po_lines = self.purchase_id.order_line
        po_products = po_lines.mapped('product_id')
        for move in self.move_ids:
            if move.state == 'cancel':
                continue
            # Done quantity: sum of move_line_ids or move.quantity (Odoo 17+)
            done_qty = sum(move.move_line_ids.mapped('quantity')) if move.move_line_ids else (getattr(move, 'quantity', 0) or 0)
            if move.purchase_line_id:
                demand = move.purchase_line_id.product_qty
                if done_qty > demand:
                    mismatches.append({
                        'type': 'qty',
                        'message': _(
                            'Product %s: received %s, PO quantity %s'
                        ) % (move.product_id.display_name, done_qty, demand),
                        'move': move,
                    })
            else:
                # Move not linked to PO line = new product on receipt
                mismatches.append({
                    'type': 'new_product',
                    'message': _('Product %s is not on the Purchase Order') % move.product_id.display_name,
                    'move': move,
                })
        return mismatches

    def _ks_has_approved_grn_mismatch(self):
        """True if this picking has an approved GRN mismatch approval request."""
        self.ensure_one()
        return bool(
            self.env['ks.grn.mismatch.approval'].search_count([
                ('picking_id', '=', self.id),
                ('state', '=', 'approved'),
            ], limit=1)
        )

    def action_ks_grn_mismatch_approval(self):
        """Open GRN Mismatch Approvals list filtered to this picking (for stat button)."""
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "ks_grn_mismatch_approval.action_ks_grn_mismatch_approval"
        )
        action["domain"] = [("picking_id", "=", self.id)]
        return action

    def button_validate(self):
        """Block validation for incoming PO receipts with quantity/product mismatch unless approved."""
        for picking in self:
            if picking.picking_type_id.code != 'incoming' or not picking.purchase_id:
                continue
            mismatches = picking._ks_get_grn_mismatches()
            if not mismatches:
                continue
            if picking._ks_has_approved_grn_mismatch():
                # Allow validation; optional: set flag so we don't check again
                picking.ks_grn_mismatch_approved = True
                continue
            # Require approval: create or reuse request and block
            Approval = picking.env['ks.grn.mismatch.approval']
            existing = Approval.search([
                ('picking_id', '=', picking.id),
                ('state', 'in', ('draft', 'pending_approval')),
            ], limit=1)
            details = '\n'.join(m['message'] for m in mismatches)
            if existing:
                existing.write({'mismatch_details': details})
                raise UserError(
                    _(
                        'This receipt has quantity or product mismatches with the Purchase Order. '
                        'An approval request already exists. Please wait for the PO approver to approve, '
                        'then update the PO if needed and validate again.\n\nDetails:\n%s'
                    ) % details
                )
            # Create new request and send for approval
            po = picking.purchase_id
            if not getattr(po, 'ks_approver_1_id', None):
                raise UserError(
                    _(
                        'This receipt has mismatches but the linked Purchase Order has no Approver 1 set. '
                        'Please configure PO approval or correct the receipt quantities/products.\n\nDetails:\n%s'
                    ) % details
                )
            approval = Approval.create({
                'picking_id': picking.id,
                'purchase_id': po.id,
                'state': 'draft',
                'request_user_id': picking.env.user.id,
                'mismatch_details': details,
            })
            approval.action_send_for_approval()
            raise UserError(
                _(
                    'This receipt has quantity or product mismatches with the Purchase Order. '
                    'An approval request has been sent to the PO approver(s). '
                    'After approval, you will be notified; then update the PO if needed and validate again.\n\nDetails:\n%s'
                ) % details
            )
        return super().button_validate()
