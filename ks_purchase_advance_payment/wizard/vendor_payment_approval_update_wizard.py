# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorPaymentApprovalUpdateWizard(models.TransientModel):
    _name = 'vendor.payment.approval.update.wizard'
    _description = 'Update Vendor Payment Approval Approvers'

    request_id = fields.Many2one(
        'vendor.payment.approval.request',
        string='Approval Request',
        required=False,
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        required=False,
    )
    ks_pm1_already_approved = fields.Boolean(string='PM1 Already Approved', default=False)
    approver_1_id = fields.Many2one(
        'res.users',
        string='Approver 1',
        required=True,
        domain="[('id', 'in', available_approver_1_ids)]",
    )
    approver_2_id = fields.Many2one(
        'res.users',
        string='Approver 2',
        required=True,
        domain="[('id', 'in', available_approver_2_ids)]",
    )
    available_approver_1_ids = fields.Many2many(
        'res.users',
        'vendor_update_wizard_avail_app1_rel',
        'wizard_id', 'user_id',
        string='Available Approver 1 Users',
        compute='_compute_available_approvers',
    )
    available_approver_2_ids = fields.Many2many(
        'res.users',
        'vendor_update_wizard_avail_app2_rel',
        'wizard_id', 'user_id',
        string='Available Approver 2 Users',
        compute='_compute_available_approvers',
    )
    ks_approval_info = fields.Html(compute='_compute_approval_info', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        request_id = self.env.context.get('default_request_id')
        payment_id = self.env.context.get('default_payment_id') or (active_id if active_model == 'account.payment' else False)

        if payment_id:
            pay = self.env['account.payment'].browse(payment_id)
            res['payment_id'] = pay.id
            pm1_line = pay.approval_line_ids.filtered(
                lambda l: l.approver_type == 'approver1' and l.state == 'approved'
            )[:1]
            if pm1_line:
                res['ks_pm1_already_approved'] = True
                res['approver_1_id'] = pm1_line.user_id.id
            else:
                existing_pm1 = pay.approval_line_ids.filtered(
                    lambda l: l.approver_type == 'approver1'
                )[:1]
                if existing_pm1:
                    res['approver_1_id'] = existing_pm1.user_id.id
            existing_pm2 = pay.approval_line_ids.filtered(
                lambda l: l.approver_type == 'approver2'
            )[:1]
            if existing_pm2:
                res['approver_2_id'] = existing_pm2.user_id.id
        elif request_id or active_model == 'vendor.payment.approval.request':
            req = self.env['vendor.payment.approval.request'].browse(request_id or active_id)
            res['request_id'] = req.id
            pm1_line = req.approval_line_ids.filtered(
                lambda l: l.approver_type == 'approver1' and l.state == 'approved'
            )[:1]
            if pm1_line:
                res['ks_pm1_already_approved'] = True
                res['approver_1_id'] = pm1_line.user_id.id
            else:
                existing_pm1 = req.approval_line_ids.filtered(
                    lambda l: l.approver_type == 'approver1'
                )[:1]
                if existing_pm1:
                    res['approver_1_id'] = existing_pm1.user_id.id
            existing_pm2 = req.approval_line_ids.filtered(
                lambda l: l.approver_type == 'approver2'
            )[:1]
            if existing_pm2:
                res['approver_2_id'] = existing_pm2.user_id.id
        return res

    @api.depends('request_id', 'payment_id')
    def _compute_available_approvers(self):
        Config = self.env['vendor.payment.approval.config']
        app1_users = Config.search([
            ('active', '=', True), ('approver_type', '=', 'approver1'),
        ]).mapped('user_id')
        app2_users = Config.search([
            ('active', '=', True), ('approver_type', '=', 'approver2'),
        ]).mapped('user_id')
        for rec in self:
            rec.available_approver_1_ids = app1_users
            rec.available_approver_2_ids = app2_users

    @api.depends('request_id', 'payment_id', 'ks_pm1_already_approved')
    def _compute_approval_info(self):
        for wiz in self:
            html = ''
            target = wiz.payment_id or wiz.request_id
            if wiz.ks_pm1_already_approved and target:
                pm1_line = target.approval_line_ids.filtered(
                    lambda l: l.approver_type == 'approver1' and l.state == 'approved'
                )[:1]
                if pm1_line:
                    html += (
                        '<div class="alert alert-success" role="alert">'
                        '<strong>&#10003; Approver 1 (%s) has already approved this request.</strong>'
                        ' Keeping the same Approver 1 will preserve their approval.'
                        '</div>'
                    ) % pm1_line.user_id.name
            html += (
                '<div class="alert alert-info">'
                '<p>Update the approvers for this payment approval request. '
                'Approval is sequential (Approver 1 must approve before Approver 2).</p>'
                '</div>'
            )
            wiz.ks_approval_info = html

    @api.onchange('approver_1_id')
    def _onchange_approver_1(self):
        if self.approver_1_id and self.approver_1_id == self.approver_2_id:
            self.approver_2_id = False

    @api.onchange('approver_2_id')
    def _onchange_approver_2(self):
        if self.approver_2_id and self.approver_2_id == self.approver_1_id:
            self.approver_1_id = False

    def action_update(self):
        self.ensure_one()
        target = self.payment_id or self.request_id
        if not target:
            raise UserError(_('No payment or approval request specified.'))

        if target.state != 'pending_approval':
            raise UserError(_('Update Approvals is only available for pending items.'))
        if not self.approver_1_id:
            raise UserError(_('Approver 1 is required.'))
        if not self.approver_2_id:
            raise UserError(_('Approver 2 is required.'))
        if self.approver_1_id == self.approver_2_id:
            raise UserError(_('Approver 1 and Approver 2 must be different users.'))

        pm1_line = target.approval_line_ids.filtered(
            lambda l: l.approver_type == 'approver1' and l.state == 'approved'
        )[:1]
        if pm1_line and pm1_line.user_id != self.approver_1_id:
            raise UserError(_(
                'Approver 1 (%s) has already approved this request and cannot be changed.'
            ) % pm1_line.user_id.name)

        preserve_pm1 = bool(pm1_line and pm1_line.user_id == self.approver_1_id)

        target.activity_unlink(['mail.mail_activity_data_todo'])

        if preserve_pm1:
            target.approval_line_ids.filtered(
                lambda l: l.approver_type == 'approver2'
            ).write({'state': 'cancelled', 'remark': _('Approver updated by %s') % self.env.user.name})
            vals = {
                'user_id': self.approver_2_id.id,
                'approver_type': 'approver2',
                'sequence': 20,
            }
            if self.payment_id:
                vals['payment_id'] = self.payment_id.id
            else:
                vals['request_id'] = self.request_id.id
            self.env['vendor.payment.approval.line'].create(vals)
            target.message_post(
                body=_('Approval request updated by %s. Approver 1 (%s) approval preserved; only Approver 2 updated.')
                % (self.env.user.name, self.approver_1_id.name),
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
        else:
            lines = [
                (5, 0, 0),
                (0, 0, {'user_id': self.approver_1_id.id, 'approver_type': 'approver1', 'sequence': 10}),
                (0, 0, {'user_id': self.approver_2_id.id, 'approver_type': 'approver2', 'sequence': 20}),
            ]
            target.sudo().write({'approval_line_ids': lines})
            target.message_post(
                body=_('Approval request updated by %s. Previous approvers cancelled.') % self.env.user.name,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

        target._notify_next_approver()
        return {'type': 'ir.actions.act_window_close'}
