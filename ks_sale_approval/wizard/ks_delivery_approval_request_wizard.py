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
    ks_is_update_mode = fields.Boolean(string='Is Update Mode', default=False)

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

    @api.depends('ks_picking_id', 'ks_approver1_user', 'ks_approver2_user', 'ks_is_update_mode')
    def _compute_approval_info(self):
        for wiz in self:
            if not wiz.ks_picking_id._has_delivery_approval_config():
                wiz.ks_approval_info = '<p>No delivery approval configuration found.</p>'
                continue
            config = wiz.ks_picking_id._get_delivery_approval_config()
            picking = wiz.ks_picking_id
            html = ''

            if wiz.ks_is_update_mode and picking.ks_validate_pm1_approved and picking.ks_validate_pm1_id:
                html += (
                    '<div class="alert alert-success" role="alert">'
                    '<strong>&#10003; Approver 1 (%s) has already approved this request.</strong>'
                    ' Keeping the same Approver 1 will preserve their approval.'
                    '</div>'
                ) % picking.ks_validate_pm1_id.name

            html += '<div class="alert alert-info">'
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
        picking = self.ks_picking_id

        # If PM1 is unchanged and already approved, preserve their approval
        preserve_pm1 = (
            is_update
            and picking.ks_validate_pm1_id
            and picking.ks_validate_pm1_id == self.ks_approver1_user
            and picking.ks_validate_pm1_approved
        )

        if is_update:
            # Cleanup only on OK — wizard Cancel leaves everything untouched
            # PM1's activity is already marked done when PM1 approves; only PM2's will be active
            picking._ks_cancel_delivery_activities()
            write_vals = {
                'ks_validate_pm1_id': False,
                'ks_validate_pm2_id': False,
                'ks_validate_pm2_approved': False,
            }
            if not preserve_pm1:
                write_vals['ks_validate_pm1_approved'] = False
            picking.write(write_vals)
            msg = (
                _('Approval request updated by %s. Approver 1 (%s) approval preserved; only Approver 2 updated.')
                % (self.env.user.name, picking.ks_validate_pm1_id.name)
                if preserve_pm1
                else _('Approval request updated by %s. Previous approvers cancelled.') % self.env.user.name
            )
            picking.message_post(body=msg, message_type='notification', subtype_xmlid='mail.mt_note')
            # Temporarily restore pre-approval state so ks_do_request_delivery_approval guard passes
            pre_state = picking.ks_pre_approval_state or 'assigned'
            picking.write({'state': pre_state})

        picking.ks_do_request_delivery_approval(
            pm1_user=self.ks_approver1_user,
            pm2_user=self.ks_approver2_user if self.ks_approver2_user else None,
            reason=self.ks_reason,
        )

        if preserve_pm1:
            # ks_do_request_delivery_approval reset pm1_approved — restore it
            picking.write({'ks_validate_pm1_approved': True})
            # Remove the fresh PM1 activity (PM1 already approved)
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', picking.id),
                ('user_id', '=', picking.ks_validate_pm1_id.id),
                ('summary', 'ilike', 'Delivery Approval'),
            ]).unlink()
            # Create PM2 activity now (mirrors what happens when PM1 approves)
            if picking.ks_validate_pm2_id:
                picking._create_delivery_approval_activity(picking.ks_validate_pm2_id, 'Validate')

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        # If wizard was opened for a fresh approval (not update) and user cancels before
        # selecting approvers, reset picking back to its pre-approval state so Validate
        # button becomes accessible again.
        picking = self.ks_picking_id
        if picking and picking.state == 'approval_pending' and not picking.ks_validate_pm1_id:
            pre_state = picking.ks_pre_approval_state or 'assigned'
            picking.write({
                'state': pre_state,
                'ks_pre_approval_state': False,
            })
        return {'type': 'ir.actions.act_window_close'}
