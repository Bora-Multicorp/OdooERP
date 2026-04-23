# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsEditApprovalRequestWizard(models.TransientModel):
    _name = 'ks.sale.edit.approval.request.wizard'
    _description = 'KS Sale Edit Approval Request Wizard'

    ks_sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
    )
    
    # Available approvers (computed from config)
    ks_approver1_user_ids = fields.Many2many(
        'res.users',
        compute='_compute_approver_user_ids',
        string='Available Approver 1 Users',
        store=False,
    )
    ks_approver2_user_ids = fields.Many2many(
        'res.users',
        compute='_compute_approver_user_ids',
        string='Available Approver 2 Users',
        store=False,
    )
    
    # Filtered approvers (excluding selected user from other field)
    ks_approver1_filtered_ids = fields.Many2many(
        'res.users',
        compute='_compute_filtered_approver_ids',
        string='Filtered Approver 1 Users',
        store=False,
    )
    ks_approver2_filtered_ids = fields.Many2many(
        'res.users',
        compute='_compute_filtered_approver_ids',
        string='Filtered Approver 2 Users',
        store=False,
    )
    
    # Selected approvers
    ks_approver1_user = fields.Many2one(
        'res.users',
        string='Approver 1',
        required=True,
        domain="[('id', 'in', ks_approver1_filtered_ids)]",
        help='Select an approver from the configured Approval 1 users',
    )
    ks_approver2_user = fields.Many2one(
        'res.users',
        string='Approver 2',
        domain="[('id', 'in', ks_approver2_filtered_ids)]",
        help='Select an approver from the configured Approval 2 users (required for dual approval mode)',
    )
    
    ks_approval_info = fields.Html(
        string='Approval Information',
        compute='_compute_approval_info',
        readonly=True,
    )
    ks_show_approver2 = fields.Boolean(
        string='Show Approver 2',
        compute='_compute_show_approver2',
        help='True if dual approval mode is enabled',
    )
    ks_is_update_mode = fields.Boolean(string='Is Update Mode', default=False)

    @api.depends('ks_sale_order_id')
    def _compute_show_approver2(self):
        """Compute visibility of Approver 2 field based on approval mode"""
        for wizard in self:
            if not wizard.ks_sale_order_id:
                wizard.ks_show_approver2 = False
                continue
            
            order = wizard.ks_sale_order_id
            if not order._has_approval_config():
                wizard.ks_show_approver2 = False
                continue
            
            config = order._get_approval_config()
            wizard.ks_show_approver2 = config.is_dual_approval()

    @api.depends('ks_sale_order_id')
    def _compute_approver_user_ids(self):
        """Compute available approvers from config"""
        for wizard in self:
            if not wizard.ks_sale_order_id:
                wizard.ks_approver1_user_ids = False
                wizard.ks_approver2_user_ids = False
                continue
            
            order = wizard.ks_sale_order_id
            if not order._has_approval_config():
                wizard.ks_approver1_user_ids = False
                wizard.ks_approver2_user_ids = False
                continue
            
            config = order._get_approval_config()
            wizard.ks_approver1_user_ids = config.ks_edit_pm1_ids
            wizard.ks_approver2_user_ids = config.ks_edit_pm2_ids

    @api.depends('ks_approver1_user_ids', 'ks_approver2_user_ids', 'ks_approver1_user', 'ks_approver2_user')
    def _compute_filtered_approver_ids(self):
        """Compute filtered approver lists excluding the selected user from the other field"""
        for wizard in self:
            # Approver 1 filtered list: exclude selected Approver 2
            if wizard.ks_approver1_user_ids:
                if wizard.ks_approver2_user:
                    wizard.ks_approver1_filtered_ids = wizard.ks_approver1_user_ids - wizard.ks_approver2_user
                else:
                    wizard.ks_approver1_filtered_ids = wizard.ks_approver1_user_ids
            else:
                wizard.ks_approver1_filtered_ids = False
            
            # Approver 2 filtered list: exclude selected Approver 1
            if wizard.ks_approver2_user_ids:
                if wizard.ks_approver1_user:
                    wizard.ks_approver2_filtered_ids = wizard.ks_approver2_user_ids - wizard.ks_approver1_user
                else:
                    wizard.ks_approver2_filtered_ids = wizard.ks_approver2_user_ids
            else:
                wizard.ks_approver2_filtered_ids = False

    @api.depends('ks_sale_order_id', 'ks_approver1_user', 'ks_approver2_user', 'ks_is_update_mode')
    def _compute_approval_info(self):
        """Compute approval information message"""
        for wizard in self:
            if not wizard.ks_sale_order_id:
                wizard.ks_approval_info = ''
                continue

            order = wizard.ks_sale_order_id
            if not order._has_approval_config():
                wizard.ks_approval_info = _('<p>No approval configuration found.</p>')
                continue

            config = order._get_approval_config()
            info_html = ''

            if wizard.ks_is_update_mode and order.ks_edit_pm1_approved and order.ks_edit_pm1_id:
                info_html += (
                    '<div class="alert alert-success" role="alert">'
                    '<strong>&#10003; Approver 1 (%s) has already approved this request.</strong>'
                    ' Keeping the same Approver 1 will preserve their approval.'
                    '</div>'
                ) % order.ks_edit_pm1_id.name

            info_html += '<div class="alert alert-info">'
            info_html += '<h5><strong>Edit Request</strong></h5>'
            info_html += '<p>You are about to send an edit request for this Sale Order.</p>'

            if config.is_dual_approval():
                info_html += '<p><strong>Note:</strong> Both Approver 1 and Approver 2 approval is required. '
                info_html += 'Approver 2 cannot approve until Approver 1 has approved.</p>'
            else:
                info_html += '<p><strong>Note:</strong> Approver 1 approval is required.</p>'

            info_html += '</div>'
            wizard.ks_approval_info = info_html

    @api.onchange('ks_approver1_user')
    def _onchange_approver1_user(self):
        """Clear Approver 2 if it matches Approver 1, and update filtered lists"""
        if self.ks_approver1_user and self.ks_approver2_user == self.ks_approver1_user:
            self.ks_approver2_user = False
        # Trigger recomputation of filtered lists
        self._compute_filtered_approver_ids()

    @api.onchange('ks_approver2_user')
    def _onchange_approver2_user(self):
        """Clear Approver 1 if it matches Approver 2, and update filtered lists"""
        if self.ks_approver2_user and self.ks_approver1_user == self.ks_approver2_user:
            self.ks_approver1_user = False
        # Trigger recomputation of filtered lists
        self._compute_filtered_approver_ids()

    def action_confirm_request(self):
        """Proceed with sending the edit request - open reason wizard.

        When opened via 'Update Edit Approvals' (ks_is_update=True), cleanup
        runs here (on OK) — never on wizard Cancel.
        """
        self.ensure_one()
        if not self.ks_approver1_user:
            raise UserError(_("Please select Approver 1."))

        order = self.ks_sale_order_id
        config = order._get_approval_config()

        if self.ks_show_approver2 and not self.ks_approver2_user:
            raise UserError(_("Please select Approver 2 (required for dual approval mode)."))

        is_update = self.env.context.get('ks_is_update', False)

        # If PM1 is unchanged and already approved, preserve their approval
        preserve_pm1 = (
            is_update
            and order.ks_edit_pm1_id
            and order.ks_edit_pm1_id == self.ks_approver1_user
            and order.ks_edit_pm1_approved
        )

        if is_update:
            if preserve_pm1:
                # Only cancel PM2's pending activity; PM1 already approved
                if order.ks_edit_pm2_id:
                    self.env['mail.activity'].sudo().search([
                        ('res_model', '=', order._name),
                        ('res_id', '=', order.id),
                        ('user_id', '=', order.ks_edit_pm2_id.id),
                        ('summary', 'ilike', 'Edit'),
                    ]).unlink()
                # Update PM2 without resetting PM1 approval or state
                order.write({
                    'ks_edit_pm2_id': self.ks_approver2_user.id if self.ks_approver2_user else False,
                    'ks_edit_pm2_approved': False,
                })
                order.message_post(
                    body=_("Edit approval request updated by %s. Approver 1 (%s) approval preserved; only Approver 2 updated.")
                    % (self.env.user.name, order.ks_edit_pm1_id.name),
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
                return {'type': 'ir.actions.act_window_close'}
            else:
                order._ks_cancel_workflow_activities('edit', mark_done=False)
                order.write({
                    'state': 'sale',
                    'ks_edit_pm1_id': False,
                    'ks_edit_pm2_id': False,
                    'ks_edit_pm1_approved': False,
                    'ks_edit_pm2_approved': False,
                    'ks_edit_approved': False,
                })
                order.message_post(
                    body=_("Edit approval request updated by %s. Previous approvers cancelled.") % self.env.user.name,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )

        # Store new approvers on the sale order
        order.write({
            'ks_edit_pm1_id': self.ks_approver1_user.id,
            'ks_edit_pm2_id': self.ks_approver2_user.id if self.ks_approver2_user else False,
        })

        # Open reason wizard
        return {
            'name': _('Request Edit Access'),
            'type': 'ir.actions.act_window',
            'res_model': 'ks.sale.reject.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_sale_order_id': order.id,
                'default_ks_action_type': 'edit_request',
            },
        }

    def action_cancel(self):
        """Cancel the approval request - do nothing"""
        return {'type': 'ir.actions.act_window_close'}

