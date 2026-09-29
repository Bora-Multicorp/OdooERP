# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class VendorPaymentApprovalSubmitWizard(models.TransientModel):
    _name = 'vendor.payment.approval.submit.wizard'
    _description = 'Submit Vendor Payment Approval Request'

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
    ks_approval_mode = fields.Selection([
        ('single', 'Single Level Approval'),
        ('two_way', 'Two Level Approval'),
    ], string='Approval Mode', compute='_compute_available_approvers')
    approver_1_id = fields.Many2one(
        'res.users',
        string='Approver 1',
        required=True,
        domain="[('id', 'in', available_approver_1_ids)]",
        help='First approver. Must approve before Approver 2.',
    )
    approver_2_id = fields.Many2one(
        'res.users',
        string='Approver 2',
        required=False,
        domain="[('id', 'in', available_approver_2_ids)]",
        help='Second approver. Approves after Approver 1.',
    )
    available_approver_1_ids = fields.Many2many(
        'res.users',
        'vendor_submit_wizard_avail_app1_rel',
        'wizard_id', 'user_id',
        string='Available Approver 1 Users',
        compute='_compute_available_approvers',
    )
    available_approver_2_ids = fields.Many2many(
        'res.users',
        'vendor_submit_wizard_avail_app2_rel',
        'wizard_id', 'user_id',
        string='Available Approver 2 Users',
        compute='_compute_available_approvers',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        default_req = self.env.context.get('default_request_id')
        default_pay = self.env.context.get('default_payment_id')

        if default_pay or active_model == 'account.payment':
            res['payment_id'] = default_pay or active_id
        elif default_req or active_model == 'vendor.payment.approval.request':
            res['request_id'] = default_req or active_id
        elif active_id:
            res['request_id'] = active_id

        Config = self.env['vendor.payment.approval.config'].sudo().get_config()
        if Config:
            if ('approver_1_id' not in res or not res.get('approver_1_id')) and Config.ks_approver_1_ids:
                if len(Config.ks_approver_1_ids) == 1:
                    res['approver_1_id'] = Config.ks_approver_1_ids[0].id
            if ('approver_2_id' not in res or not res.get('approver_2_id')) and Config.ks_approver_2_ids:
                if Config.ks_approval_mode == 'two_way' and len(Config.ks_approver_2_ids) == 1:
                    res['approver_2_id'] = Config.ks_approver_2_ids[0].id
        return res

    @api.depends('request_id', 'payment_id')
    def _compute_available_approvers(self):
        Config = self.env['vendor.payment.approval.config'].sudo().get_config()
        if Config:
            app1_users = Config.ks_approver_1_ids
            app2_users = Config.ks_approver_2_ids
            mode = Config.ks_approval_mode
        else:
            app1_users = self.env['res.users']
            app2_users = self.env['res.users']
            mode = 'two_way'
        for rec in self:
            rec.available_approver_1_ids = app1_users
            rec.available_approver_2_ids = app2_users
            rec.ks_approval_mode = mode

    @api.constrains('approver_1_id', 'approver_2_id')
    def _check_approvers_different(self):
        Config = self.env['vendor.payment.approval.config'].sudo().get_config()
        is_two_way = Config.is_two_way_approval() if Config else True
        for rec in self:
            if is_two_way and rec.approver_1_id and rec.approver_2_id and rec.approver_1_id == rec.approver_2_id:
                raise UserError(_('Approver 1 and Approver 2 must be different users.'))

    @api.onchange('approver_1_id')
    def _onchange_approver_1(self):
        if self.approver_1_id and self.approver_1_id == self.approver_2_id:
            self.approver_2_id = False

    def action_submit(self):
        """Validate, create approval lines with the chosen approvers, and move to pending_approval."""
        self.ensure_one()
        Config = self.env['vendor.payment.approval.config'].sudo().get_config()
        if not Config:
            raise UserError(_('No active Vendor Payment Approval Configuration found.'))
        is_two_way = Config.is_two_way_approval()

        if not self.approver_1_id:
            raise UserError(_('Approver 1 is required.'))
        if is_two_way:
            if not self.approver_2_id:
                raise UserError(_('Approver 2 is required.'))
            if self.approver_1_id == self.approver_2_id:
                raise UserError(_('Approver 1 and Approver 2 must be different users.'))

        lines = [
            (5, 0, 0),
            (0, 0, {
                'user_id': self.approver_1_id.id,
                'approver_type': 'approver1',
                'sequence': 10,
            }),
        ]
        if is_two_way and self.approver_2_id:
            lines.append((0, 0, {
                'user_id': self.approver_2_id.id,
                'approver_type': 'approver2',
                'sequence': 20,
            }))

        if self.payment_id:
            pay = self.payment_id
            if pay.state != 'draft':
                raise UserError(_('Only draft payments can be submitted.'))
            pay.sudo().write({
                'state': 'pending_approval',
                'approval_line_ids': lines,
            })
            pay._notify_next_approver()
            return {'type': 'ir.actions.act_window_close'}

        req = self.request_id
        if not req:
            raise UserError(_('No approval request or payment specified.'))
        if req.state != 'draft':
            raise UserError(_('Only draft requests can be submitted.'))
        if req.approval_type == 'with_bill' and not req.purchase_order_id.has_vendor_bill:
            raise UserError(_(
                'Cannot submit "Payment approval with bill": '
                'Purchase Order %s does not have a posted vendor bill yet.'
            ) % req.purchase_order_id.name)

        req.sudo().write({
            'state': 'pending_approval',
            'approval_line_ids': lines,
        })
        req._notify_next_approver()
        return {'type': 'ir.actions.act_window_close'}

