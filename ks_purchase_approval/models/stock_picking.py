# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # ===== GRN Approval (receipt: over-receipt or new product) =====
    ks_grn_approval_state = fields.Selection(
        [
            ('normal', 'Normal'),
            ('pending_approval', 'Pending Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='GRN Approval',
        default='normal',
        copy=False,
        help='Set to Pending when received qty exceeds demand or new product is added; approval sent to PO approvers.',
    )
    ks_grn_request_date = fields.Datetime(string='GRN Approval Request Date', copy=False)
    ks_grn_request_user_id = fields.Many2one('res.users', string='GRN Requested By', copy=False)
    ks_grn_pm1_approved = fields.Boolean(string='Approver 1 Approved', default=False, copy=False)
    ks_grn_pm2_approved = fields.Boolean(string='Approver 2 Approved', default=False, copy=False)
    ks_grn_pm1_reason = fields.Text(string='Approver 1 Reason', copy=False)
    ks_grn_pm2_reason = fields.Text(string='Approver 2 Reason', copy=False)
    ks_grn_reject_reason = fields.Text(string='Rejection Reason', copy=False)
    ks_grn_reject_user_id = fields.Many2one('res.users', string='Rejected By', copy=False)

    ks_grn_show_approve_button = fields.Boolean(
        string='Show GRN Approve Button',
        compute='_compute_ks_grn_approve_reject_buttons',
    )
    ks_grn_show_reject_button = fields.Boolean(
        string='Show GRN Reject Button',
        compute='_compute_ks_grn_approve_reject_buttons',
    )

    @api.depends('ks_grn_approval_state', 'purchase_id', 'purchase_id.ks_approver_1_id', 'purchase_id.ks_approver_2_id', 'ks_grn_pm1_approved')
    def _compute_ks_grn_approve_reject_buttons(self):
        for p in self:
            p.ks_grn_show_approve_button = False
            p.ks_grn_show_reject_button = False
            if p.ks_grn_approval_state != 'pending_approval' or not p.purchase_id:
                continue
            po = p.purchase_id
            cur = self.env.user
            if cur == po.ks_approver_1_id and not p.ks_grn_pm1_approved:
                p.ks_grn_show_approve_button = True
                p.ks_grn_show_reject_button = True
            elif po.ks_approver_2_id and cur == po.ks_approver_2_id and p.ks_grn_pm1_approved:
                p.ks_grn_show_approve_button = True
                p.ks_grn_show_reject_button = True

    def _ks_grn_has_over_receipt_or_new_product(self):
        """True if any move has done qty > demand or a product not on the PO."""
        self.ensure_one()
        if not self.purchase_id or self.picking_type_id.code != 'incoming':
            return False
        po_product_ids = self.purchase_id.order_line.mapped('product_id').ids
        for move in self.move_ids:
            if not move.purchase_line_id:
                # New product (not on PO)
                return True
            if move.product_id.id not in po_product_ids:
                return True
            demand = move.product_uom_qty
            done = self._ks_grn_get_done_quantity(move)
            if done > demand:
                return True
        return False

    def _ks_grn_get_done_quantity(self, move):
        """Return done quantity for a move (quantity_done or sum of move_line_ids)."""
        if hasattr(move, 'quantity_done') and move.quantity_done is not None:
            return move.quantity_done
        if move.move_line_ids:
            # Odoo 18: move_line can have 'quantity' or 'qty_done'
            if move.move_line_ids._fields.get('quantity'):
                return sum(move.move_line_ids.mapped('quantity'))
            if move.move_line_ids._fields.get('qty_done'):
                return sum(move.move_line_ids.mapped('qty_done'))
        return getattr(move, 'quantity', 0) or 0

    def _ks_grn_requires_approval(self):
        """True if receipt has over-receipt or new product and is not yet approved."""
        self.ensure_one()
        if self.ks_grn_approval_state == 'approved':
            return False
        return self._ks_grn_has_over_receipt_or_new_product()

    def _ks_grn_get_po_approvers(self):
        """Return PO's approvers (Approver 1 and Approver 2) for this receipt."""
        self.ensure_one()
        if not self.purchase_id:
            return self.env['res.users']
        po = self.purchase_id
        approvers = self.env['res.users']
        if getattr(po, 'ks_approver_1_id', None):
            approvers |= po.ks_approver_1_id
        if getattr(po, 'ks_approver_2_id', None):
            approvers |= po.ks_approver_2_id
        return approvers

    def button_validate(self):
        """Block validate when over-receipt or new product and GRN approval not yet approved."""
        for picking in self:
            if not picking.purchase_id or picking.picking_type_id.code != 'incoming':
                continue
            if picking.ks_grn_approval_state == 'rejected':
                raise UserError(_(
                    'This receipt was rejected. Please correct quantities or products and request approval again, or create a new receipt.'
                ))
            if picking._ks_grn_has_over_receipt_or_new_product():
                if picking.ks_grn_approval_state == 'pending_approval':
                    raise UserError(_(
                        'This receipt has over-received quantities or products not on the Purchase Order. '
                        'It is pending approval from the PO approvers. Please wait for approval before validating.'
                    ))
                if picking.ks_grn_approval_state != 'approved':
                    # Trigger approval request: set state and notify PO approvers
                    picking._ks_grn_request_approval()
                    raise UserError(_(
                        'This receipt has over-received quantities or products not on the Purchase Order. '
                        'An approval request has been sent to the PO approvers. You can validate after they approve.'
                    ))
        return super().button_validate()

    def _ks_grn_request_approval(self):
        """Set GRN to pending and notify PO's approvers (not the buyer)."""
        self.ensure_one()
        if not self.purchase_id or self.picking_type_id.code != 'incoming':
            return
        approvers = self._ks_grn_get_po_approvers()
        if not approvers:
            raise UserError(_(
                'No approvers are set on the Purchase Order %s. '
                'The PO must have been approved (Approver 1 / Approver 2) before a GRN approval can be requested.'
            ) % self.purchase_id.name)
        self.write({
            'ks_grn_approval_state': 'pending_approval',
            'ks_grn_request_date': fields.Datetime.now(),
            'ks_grn_request_user_id': self.env.user.id,
            'ks_grn_pm1_approved': False,
            'ks_grn_pm2_approved': False,
            'ks_grn_pm1_reason': False,
            'ks_grn_pm2_reason': False,
            'ks_grn_reject_reason': False,
            'ks_grn_reject_user_id': False,
        })
        # Notify first approver (same as PO flow)
        first_approver = self.purchase_id.ks_approver_1_id
        if first_approver:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=first_approver.id,
                note=_(
                    'GRN %s has over-received quantities or products not on the Purchase Order. '
                    'Please approve or reject this receipt.'
                ) % self.name,
                summary=_('GRN Approval: %s') % self.name,
            )
        self.message_post(
            body=_(
                'GRN approval requested by %s (received qty exceeds demand or new product added). '
                'Waiting for approval from: %s.'
            ) % (self.env.user.name, ', '.join(approvers.mapped('name'))),
        )

    def _ks_grn_do_approve(self, reason):
        """Approve GRN (called by wizard). Current user must be Approver 1 or 2."""
        self.ensure_one()
        if self.ks_grn_approval_state != 'pending_approval':
            raise UserError(_('Only receipts in Pending Approval can be approved.'))
        po = self.purchase_id
        if not po:
            raise UserError(_('This picking is not linked to a Purchase Order.'))
        current_user = self.env.user
        is_two_way = getattr(po, 'ks_pm2_approved', None) is not None
        config = self.env['ks.purchase.approval.config'].get_config()
        if config:
            is_two_way = config.ks_approval_mode == 'two_way'

        if current_user == po.ks_approver_1_id:
            if self.ks_grn_pm1_approved:
                raise UserError(_('You have already approved this GRN.'))
            self.write({
                'ks_grn_pm1_approved': True,
                'ks_grn_pm1_reason': reason or '',
            })
            self.message_post(body=_('%s approved (Approver 1). Reason: %s') % (current_user.name, reason or '-'))
            if not is_two_way or not po.ks_approver_2_id:
                self.write({'ks_grn_approval_state': 'approved'})
                self.activity_unlink(['mail.mail_activity_data_todo'])
                self._ks_grn_notify_warehouse()
            else:
                self.activity_unlink(['mail.mail_activity_data_todo'])
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=po.ks_approver_2_id.id,
                    note=_('GRN %s has been approved by Approver 1. Please approve or reject.') % self.name,
                    summary=_('GRN Approval: %s') % self.name,
                )
        elif current_user == po.ks_approver_2_id:
            if not self.ks_grn_pm1_approved:
                raise UserError(_('Approver 1 must approve before Approver 2 can approve.'))
            if self.ks_grn_pm2_approved:
                raise UserError(_('You have already approved this GRN.'))
            self.write({
                'ks_grn_pm2_approved': True,
                'ks_grn_pm2_reason': reason or '',
                'ks_grn_approval_state': 'approved',
            })
            self.message_post(body=_('%s approved (Approver 2). Reason: %s') % (current_user.name, reason or '-'))
            self.activity_unlink(['mail.mail_activity_data_todo'])
            self._ks_grn_notify_warehouse()
        else:
            raise UserError(_('You are not an approver for this GRN. Only the PO approvers can approve.'))

    def _ks_grn_do_reject(self, reason):
        """Reject GRN (called by wizard)."""
        self.ensure_one()
        if self.ks_grn_approval_state != 'pending_approval':
            raise UserError(_('Only receipts in Pending Approval can be rejected.'))
        po = self.purchase_id
        if not po or self.env.user not in (po.ks_approver_1_id | po.ks_approver_2_id):
            raise UserError(_('Only the PO approvers can reject this GRN.'))
        self.write({
            'ks_grn_approval_state': 'rejected',
            'ks_grn_reject_reason': reason or '',
            'ks_grn_reject_user_id': self.env.user.id,
        })
        self.message_post(body=_('%s rejected. Reason: %s') % (self.env.user.name, reason or '-'))
        self.activity_unlink(['mail.mail_activity_data_todo'])

    def _ks_grn_notify_warehouse(self):
        """After GRN approval, notify warehouse responsible person."""
        self.ensure_one()
        if self.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.user_id.id,
                note=_(
                    'GRN %s has been approved by the PO approvers. '
                    'You can update the PO if needed and then validate the receipt.'
                ) % self.name,
                summary=_('GRN Approved: %s') % self.name,
            )
            self.message_post(
                body=_('Warehouse responsible person (%s) has been notified.') % self.user_id.name,
            )

    def action_ks_grn_approve_wizard(self):
        """Open approve wizard for GRN."""
        self.ensure_one()
        return {
            'name': _('Approve GRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.grn.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id, 'active_id': self.id},
        }

    def action_ks_grn_reject_wizard(self):
        """Open reject wizard for GRN."""
        self.ensure_one()
        return {
            'name': _('Reject GRN'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.grn.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_picking_id': self.id, 'active_id': self.id},
        }
