# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    ks_can_register_vendor_payment = fields.Boolean(
        string='Can Register Vendor Payment',
        compute='_compute_ks_vendor_payment_fields',
        help='True if this vendor bill can show the Pay button (all linked POs have approved "with bill" payment request).',
    )
    ks_has_linked_po = fields.Boolean(
        string='Has Linked Purchase Order',
        compute='_compute_ks_vendor_payment_fields',
        help='True if this posted vendor bill has at least one linked Purchase Order.',
    )

    @api.depends(
        'move_type', 'state',
        'invoice_origin',
        'line_ids.purchase_line_id.order_id',
        'line_ids.purchase_line_id.order_id.has_approved_bill_payment_request',
    )
    def _compute_ks_vendor_payment_fields(self):
        for move in self:
            if move.move_type != 'in_invoice' or move.state != 'posted':
                move.ks_can_register_vendor_payment = True
                move.ks_has_linked_po = False
                continue

            # Primary: detect POs via line-level purchase_line_id (bills created from PO via "Create Bill")
            purchase_lines = move.line_ids.mapped('purchase_line_id').filtered(lambda l: l)
            pos = purchase_lines.mapped('order_id').filtered(lambda o: o)

            # Fallback: detect PO via invoice_origin (bills created from PO keep the PO name as origin)
            if not pos and move.invoice_origin:
                origins = [o.strip() for o in move.invoice_origin.split(',') if o.strip()]
                if origins:
                    pos = self.env['purchase.order'].search([('name', 'in', origins)])

            if not pos:
                # No PO detected — still block Pay; "Request For Payment" button will guide the user.
                move.ks_can_register_vendor_payment = False
                move.ks_has_linked_po = False
            else:
                move.ks_can_register_vendor_payment = all(po.has_approved_bill_payment_request for po in pos)
                move.ks_has_linked_po = True

    def _get_linked_purchase_orders(self):
        """Return confirmed Purchase Orders linked to this vendor bill.

        Checks line-level purchase_line_id first, then falls back to invoice_origin.
        """
        self.ensure_one()
        purchase_lines = self.line_ids.mapped('purchase_line_id').filtered(lambda l: l)
        pos = purchase_lines.mapped('order_id').filtered(lambda o: o and o.state in ('purchase', 'done'))
        if not pos and self.invoice_origin:
            origins = [o.strip() for o in self.invoice_origin.split(',') if o.strip()]
            if origins:
                pos = self.env['purchase.order'].search([
                    ('name', 'in', origins),
                    ('state', 'in', ('purchase', 'done')),
                ])
        return pos

    def action_create_bill_payment_request(self):
        """Create or open a 'with bill' payment approval request from the vendor bill."""
        self.ensure_one()
        if self.move_type != 'in_invoice' or self.state != 'posted':
            raise UserError(_('Payment request can only be created for posted vendor bills.'))

        pos = self._get_linked_purchase_orders()
        if not pos:
            raise UserError(_(
                'No confirmed Purchase Orders are linked to this vendor bill. '
                'Please link a confirmed PO to this bill first.'
            ))

        if len(pos) == 1:
            return pos.action_create_payment_approval_request_bill()

        # Multiple POs: create/open requests for all of them
        created_or_existing = self.env['vendor.payment.approval.request']
        errors = []
        for po in pos:
            try:
                existing = po.payment_approval_request_ids.filtered(
                    lambda r: r.state in ('draft', 'pending_approval') and r.approval_type == 'with_bill'
                )[:1]
                if existing:
                    created_or_existing |= existing
                else:
                    req = self.env['vendor.payment.approval.request'].create({
                        'purchase_order_id': po.id,
                        'approval_type': 'with_bill',
                    })
                    created_or_existing |= req
            except Exception as e:
                errors.append(str(e))
        if errors:
            raise UserError('\n'.join(errors))
        return {
            'name': _('Payment Approval Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.payment.approval.request',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_or_existing.ids)],
        }
