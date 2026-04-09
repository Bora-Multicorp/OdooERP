# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KsDeliveryApprovalRequestWizard(models.TransientModel):
    _name = 'ks.delivery.approval.request.wizard'
    _description = 'KS Delivery Approval Request Wizard'

    ks_picking_id = fields.Many2one('stock.picking', string='Delivery Order', required=True)

    ks_approver1_user_ids = fields.Many2many(
        'res.users', compute='_compute_approver_user_ids', store=False)
    ks_approver2_user_ids = fields.Many2many(
        'res.users', compute='_compute_approver_user_ids', store=False,
        relation='ks_del_req_wiz_approver2_rel')
    ks_approver1_filtered_ids = fields.Many2many(
        'res.users', compute='_compute_filtered_approver_ids', store=False,
        relation='ks_del_req_wiz_filtered1_rel')
    ks_approver2_filtered_ids = fields.Many2many(
        'res.users', compute='_compute_filtered_approver_ids', store=False,
        relation='ks_del_req_wiz_filtered2_rel')

    ks_approver1_user = fields.Many2one(
        'res.users', string='Approver 1', required=True,
        domain="[('id', 'in', ks_approver1_filtered_ids)]")
    ks_approver2_user = fields.Many2one(
        'res.users', string='Approver 2',
        domain="[('id', 'in', ks_approver2_filtered_ids)]")
    ks_reason = fields.Text(string='Reason', placeholder='Optional reason for this request...')
    ks_show_approver2 = fields.Boolean(compute='_compute_show_approver2')
    ks_approval_info = fields.Html(compute='_compute_approval_info', readonly=True)

    @api.depends('ks_picking_id')
    def _compute_show_approver2(self):
        for wiz in self:
            if wiz.ks_picking_id._has_delivery_approval_config():
                wiz.ks_show_approver2 = wiz.ks_picking_id._get_delivery_approval_config().is_dual_approval()
            else:
                wiz.ks_show_approver2 = False

    @api.depends('ks_picking_id')
    def _compute_approver_user_ids(self):
        for wiz in self:
            if wiz.ks_picking_id._has_delivery_approval_config():
                config = wiz.ks_picking_id._get_delivery_approval_config()
                wiz.ks_approver1_user_ids = config.ks_validate_pm1_ids
                wiz.ks_approver2_user_ids = config.ks_validate_pm2_ids
            else:
                wiz.ks_approver1_user_ids = False
                wiz.ks_approver2_user_ids = False

    @api.depends('ks_approver1_user_ids', 'ks_approver2_user_ids', 'ks_approver1_user', 'ks_approver2_user')
    def _compute_filtered_approver_ids(self):
        for wiz in self:
            wiz.ks_approver1_filtered_ids = (
                wiz.ks_approver1_user_ids - wiz.ks_approver2_user
                if wiz.ks_approver2_user else wiz.ks_approver1_user_ids
            )
            wiz.ks_approver2_filtered_ids = (
                wiz.ks_approver2_user_ids - wiz.ks_approver1_user
                if wiz.ks_approver1_user else wiz.ks_approver2_user_ids
            )

    @api.depends('ks_picking_id', 'ks_approver1_user', 'ks_approver2_user')
    def _compute_approval_info(self):
        for wiz in self:
            if not wiz.ks_picking_id._has_delivery_approval_config():
                wiz.ks_approval_info = '<p>No delivery approval configuration found.</p>'
                continue
            config = wiz.ks_picking_id._get_delivery_approval_config()
            html = '<div class="alert alert-info">'
            html += '<h5><strong>Delivery Validation Approval Request</strong></h5>'
            html += '<p>You are about to submit this delivery for approval before validation.</p>'
            if config.is_dual_approval():
                html += ('<p><strong>Note:</strong> Both Approver 1 and Approver 2 approval is required. '
                         'Approver 2 cannot approve until Approver 1 has approved.</p>')
            else:
                html += '<p><strong>Note:</strong> Approver 1 approval is required.</p>'
            html += '</div>'
            wiz.ks_approval_info = html

    @api.onchange('ks_approver1_user')
    def _onchange_approver1(self):
        if self.ks_approver1_user and self.ks_approver2_user == self.ks_approver1_user:
            self.ks_approver2_user = False

    @api.onchange('ks_approver2_user')
    def _onchange_approver2(self):
        if self.ks_approver2_user and self.ks_approver1_user == self.ks_approver2_user:
            self.ks_approver1_user = False

    def action_confirm_request(self):
        self.ensure_one()
        if not self.ks_approver1_user:
            raise UserError(_('Please select Approver 1.'))
        if self.ks_show_approver2 and not self.ks_approver2_user:
            raise UserError(_('Please select Approver 2 (required for dual approval mode).'))

        is_update = self.env.context.get('ks_is_update', False)
        if is_update:
            # Cleanup only on OK — wizard Cancel leaves everything untouched
            self.ks_picking_id._ks_cancel_delivery_activities()
            self.ks_picking_id.write({
                'ks_validate_pm1_id': False,
                'ks_validate_pm2_id': False,
                'ks_validate_pm1_approved': False,
                'ks_validate_pm2_approved': False,
            })
            self.ks_picking_id.message_post(
                body=_('Approval request updated by %s. Previous approvers cancelled.') % self.env.user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            # Temporarily restore pre-approval state so ks_do_request_delivery_approval guard passes
            pre_state = self.ks_picking_id.ks_pre_approval_state or 'assigned'
            self.ks_picking_id.write({'state': pre_state})

        self.ks_picking_id.ks_do_request_delivery_approval(
            pm1_user=self.ks_approver1_user,
            pm2_user=self.ks_approver2_user if self.ks_approver2_user else None,
            reason=self.ks_reason,
        )
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
