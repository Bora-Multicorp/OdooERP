# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsApprovalConfirmationWizard(models.TransientModel):
    _name = 'ks.approval.confirmation.wizard'
    _description = 'KS Approval Confirmation Wizard'

    ks_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True,
    )
    ks_approver_1_id = fields.Many2one(
        'res.users',
        string='Approver 1',
        required=True,
        domain="[('id', 'in', ks_available_approver_1_ids)]",
        help='First approver for confirmation (must approve before Approver 2)',
    )
    ks_approver_2_id = fields.Many2one(
        'res.users',
        string='Approver 2',
        required=False,
        domain="[('id', 'in', ks_available_approver_2_ids)]",
        help='Second approver for confirmation (approves after Approver 1). Required only for Two Level Approval mode.',
    )
    ks_is_two_way_approval = fields.Boolean(
        string='Is Two Way Approval',
        compute='_compute_approval_mode',
        help='True if two-way approval mode is enabled',
    )
    ks_available_approver_1_ids = fields.Many2many(
        'res.users',
        string='Available Approver 1 Users',
        compute='_compute_available_approvers',
    )
    ks_available_approver_2_ids = fields.Many2many(
        'res.users',
        string='Available Approver 2 Users',
        compute='_compute_available_approvers',
    )
    ks_is_update_mode = fields.Boolean(string='Is Update Mode', default=False)
    ks_pm1_approved_status = fields.Html(
        string='PM1 Approval Status',
        compute='_compute_pm1_approved_status',
        readonly=True,
    )

    @api.depends('ks_purchase_order_id')
    def _compute_available_approvers(self):
        """Compute available approvers based on configuration"""
        for record in self:
            if record.ks_purchase_order_id and record.ks_purchase_order_id._has_approval_config():
                config = record.ks_purchase_order_id._get_approval_config()
                # Get users configured as Approver 1
                record.ks_available_approver_1_ids = config.get_approvers_by_level('approver_1')
                
                # Get users configured as Approver 2
                record.ks_available_approver_2_ids = config.get_approvers_by_level('approver_2')
            else:
                record.ks_available_approver_1_ids = False
                record.ks_available_approver_2_ids = False
    
    @api.depends('ks_purchase_order_id')
    def _compute_approval_mode(self):
        """Compute approval mode"""
        for record in self:
            if record.ks_purchase_order_id and record.ks_purchase_order_id._has_approval_config():
                config = record.ks_purchase_order_id._get_approval_config()
                record.ks_is_two_way_approval = config.is_two_way_approval()
            else:
                record.ks_is_two_way_approval = False

    @api.depends('ks_purchase_order_id', 'ks_is_update_mode')
    def _compute_pm1_approved_status(self):
        for wizard in self:
            order = wizard.ks_purchase_order_id
            if wizard.ks_is_update_mode and order and order.ks_pm1_approved and order.ks_approver_1_id:
                name = order.ks_approver_1_id.name
                wizard.ks_pm1_approved_status = _(
                    '<div class="alert alert-success" role="alert">'
                    '<strong>&#10003; Approver 1 (%s) has already approved this request.</strong>'
                    ' Keeping the same Approver 1 will preserve their approval.'
                    '</div>'
                ) % name
            else:
                wizard.ks_pm1_approved_status = False

    @api.constrains('ks_approver_1_id', 'ks_approver_2_id')
    def _check_approvers_different(self):
        """Ensure Approver 1 and Approver 2 are different users"""
        for record in self:
            if record.ks_approver_1_id and record.ks_approver_2_id:
                if record.ks_approver_1_id == record.ks_approver_2_id:
                    raise UserError(_("Approver 1 and Approver 2 must be different users."))

    @api.onchange('ks_approver_1_id')
    def _onchange_approver_1(self):
        """Clear Approver 2 if it's the same as Approver 1"""
        if self.ks_approver_1_id and self.ks_approver_2_id:
            if self.ks_approver_1_id == self.ks_approver_2_id:
                self.ks_approver_2_id = False

    @api.onchange('ks_approver_2_id')
    def _onchange_approver_2(self):
        """Clear Approver 1 if it's the same as Approver 2"""
        if self.ks_approver_1_id and self.ks_approver_2_id:
            if self.ks_approver_1_id == self.ks_approver_2_id:
                self.ks_approver_1_id = False

    def action_confirm_send(self):
        """User confirms to send the approval request with selected approvers.

        When opened via 'Update Approvals' (ks_is_update=True in context), the old
        activities and fields are reset HERE — only after the user clicks OK.
        Clicking the wizard Cancel button leaves everything untouched.
        """
        self.ensure_one()
        if not self.ks_approver_1_id:
            raise UserError(_("Approver 1 is required."))

        # Check approval mode
        if self.ks_is_two_way_approval:
            if not self.ks_approver_2_id:
                raise UserError(_("Approver 2 is required for Two Level Approval mode."))
            if self.ks_approver_1_id == self.ks_approver_2_id:
                raise UserError(_("Approver 1 and Approver 2 must be different users."))
            approver_2_id = self.ks_approver_2_id.id
        else:
            approver_2_id = self.ks_approver_2_id.id if self.ks_approver_2_id else False

        order = self.ks_purchase_order_id
        is_update = self.env.context.get('ks_is_update', False)

        # If PM1 is unchanged and already approved, preserve their approval
        preserve_pm1 = (
            is_update
            and order.ks_approver_1_id
            and order.ks_approver_1_id == self.ks_approver_1_id
            and order.ks_pm1_approved
        )

        if is_update:
            # Cancel old confirm-workflow activities (PM1's activity is already done; only PM2's will be found)
            order._ks_cancel_workflow_activities('confirm', mark_done=False)
            # Reset fields and return to 'sent' so _ks_send_to_pending_approval guard passes
            write_vals = {
                'state': 'sent',
                'ks_approver_1_id': False,
                'ks_approver_2_id': False,
                'ks_pm2_approved': False,
                'ks_pm2_reason': False,
            }
            if not preserve_pm1:
                write_vals['ks_pm1_approved'] = False
                write_vals['ks_pm1_reason'] = False
            order.write(write_vals)
            msg = (
                _("Approval request updated by %s. Approver 1 (%s) approval preserved; only Approver 2 updated.")
                % (self.env.user.name, order.ks_approver_1_id.name)
                if preserve_pm1
                else _("Approval request updated by %s. Previous approvers cancelled.") % self.env.user.name
            )
            order.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')

        order._ks_send_to_pending_approval(self.ks_approver_1_id.id, approver_2_id)

        if preserve_pm1:
            # _ks_send_to_pending_approval reset pm1_approved — restore it
            order.write({'ks_pm1_approved': True})
            # Remove the fresh PM1 activity (PM1 already approved)
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', order._name),
                ('res_id', '=', order.id),
                ('user_id', '=', order.ks_approver_1_id.id),
                ('summary', 'ilike', 'PO Approval Request for'),
            ]).unlink()
            # Create PM2 activity now (mirrors what happens when PM1 approves)
            if order.ks_approver_2_id:
                order._create_approval_activity(
                    user_id=order.ks_approver_2_id.id,
                    summary=_('PO Approval Request for: %s - Approver 1 Approved') % order.name,
                    note=_('Purchase Order %s has been approved by Approver 1 (%s). Please review and approve or reject. Reason: %s') % (
                        order.name, order.ks_approver_1_id.name, order.ks_pm1_reason or '',
                    ),
                )

        return {'type': 'ir.actions.act_window_close'}

