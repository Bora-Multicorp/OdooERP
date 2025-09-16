# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree

_logger = logging.getLogger(__name__)


class PaymentTermApproval(models.Model):
    _inherit = 'sale.order'
    _description = 'Payment Approval Queue'

    # Boolean fields to control workflow
    is_pending_approval = fields.Boolean(string="Pending Credit Approval", default=False, copy=False)
    is_payment_approved = fields.Boolean(string="Credit Approved", default=False, copy=False)
    is_payment_rejected = fields.Boolean(string="Credit Rejected", default=False, copy=False)

    credit_due_date = fields.Date(string="Credit Due Date")

    credit_approval_users_ids = fields.One2many(
        'payment.term.approval.users',
        'payment_approval_id',
        string='Approval Authorities',
        help='Approval Authority Details'
    )
    credit_assigned_to = fields.Many2one('res.users', string='Assigned To')
    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_users', store=True)

    # Computed field for showing banner message
    credit_status_message = fields.Html(
        string="Credit Status",
        compute="_compute_credit_status_message"
    )

    #
    # # Default Approval Users setup
    # @api.model
    # def default_get(self, fields_list):
    #     defaults = super().default_get(fields_list)
    #     payment_approval_users = self.env['payment.term.approval.config'].sudo().search([])
    #
    #     if payment_approval_users:
    #         approval_user_vals = []
    #         for approval in payment_approval_users:
    #             approval_user_vals.append((0, 0, {
    #                 'sequence': approval.sequence,
    #                 'user_id': approval.user_id.id,
    #             }))
    #         defaults['credit_approval_users_ids'] = approval_user_vals
    #     return defaults

    def action_confirm(self):
        """Prevent confirmation if credit payment term is not yet approved."""
        for order in self:
            # if order.user_id != self.env.user:
            #     raise ValidationError(_("You can not confirm this Sale Order."))
            if order.payment_term_id and order.payment_term_id.name == "Credit Payment":
                if not order.is_payment_approved:
                    raise ValidationError(
                        _("You cannot confirm this Sale Order until the Credit Payment Term is approved.")
                    )
                states = order.credit_approval_users_ids.mapped('state')
                if not states or any(s != 'approve' for s in states):
                    raise ValidationError(
                        _("You cannot confirm this Sale Order until All Credit Payment approvers approve it.")
                    )

                if not order.is_payment_approved:
                    raise ValidationError(
                        _("Credit Payment Term must be fully approved before confirmation.")
                    )
        return super(PaymentTermApproval, self).action_confirm()

    @api.depends('credit_approval_users_ids.user_id')
    def _compute_existing_users(self):
        for record in self:
            if record.credit_approval_users_ids:
                record.existing_user_ids = [(6, 0, record.credit_approval_users_ids.mapped('user_id').ids)]
            else:
                record.existing_user_ids = [(6, 0, [])]

    # New method for computing banner message
    @api.depends('is_pending_approval', 'is_payment_approved', 'is_payment_rejected')
    def _compute_credit_status_message(self):
        for order in self:
            msg = ""
            if order.payment_term_id and order.payment_term_id.name == "Credit Payment":
                if order.is_payment_rejected:
                    msg = "<div class='alert alert-danger'>⚠️ Payment Term Credit has been <b>Rejected</b>.</div>"
                elif order.is_payment_approved:
                    msg = "<div class='alert alert-success'>✅ Payment Term Credit has been <b>Approved</b>.</div>"
                elif order.is_pending_approval:
                    msg = "<div class='alert alert-warning'>⏳ Payment Credit Term is in <b>Pending Approval</b>.</div>"
            order.credit_status_message = msg

    # Submit for approval
    # def confirm_submit_form(self):
    #     if not self.credit_approval_users_ids:
    #         raise ValidationError(_("Please Add Approval Authority before Submit Request."))
    #
    #     # Use a single write to set all boolean fields correctly
    #     for order in self:
    #         order.write({
    #             'is_pending_approval': True,
    #             'is_p
    #             ayment_approved': False,
    #             'is_payment_rejected': False,
    #         })
    #         order._update_credit_assigned_to()

    def confirm_submit_form(self):
        for order in self:
            # if approval users are not already set, fetch from config
            if not order.credit_approval_users_ids:
                payment_approval_users = self.env['payment.term.approval.config'].sudo().search([])
                if not payment_approval_users:
                    raise ValidationError(_("Please configure Approval Authorities before Submit Request."))

                approval_user_vals = []
                for approval in payment_approval_users:
                    approval_user_vals.append((0, 0, {
                        'sequence': approval.sequence,
                        'user_id': approval.user_id.id,
                    }))
                order.write({
                    'credit_approval_users_ids': approval_user_vals
                })

            # Update status booleans
            order.write({
                'is_pending_approval': True,
                'is_payment_approved': False,
                'is_payment_rejected': False,
            })

            # Assign first approver user (or any custom logic)
            order._update_credit_assigned_to()

    def action_reset_credit_approval(self):
        for order in self:
            if not order.is_payment_rejected:
                raise ValidationError(_("Reset is only allowed if the credit approval was rejected."))

                # Keep old lines as history, create new lines
                # Keep old lines as history, create new lines
            for line in order.credit_approval_users_ids:
                if not line.remark:
                    # approver never acted in this cycle
                    line.write({
                        'state': 'suspended',
                        'remark': 'Suspended',
                        'action_date': fields.Datetime.now(),
                    })
            approval_user_vals = []
            payment_approval_users = self.env['payment.term.approval.config'].sudo().search([])
            for approval in payment_approval_users:
                approval_user_vals.append((0, 0, {
                    'sequence': approval.sequence,
                    'user_id': approval.user_id.id,
                }))
            order.write({'credit_approval_users_ids': approval_user_vals})

            # Reset flags
            order.write({
                'is_payment_rejected': False,
                'is_payment_approved': False,
                'is_pending_approval': False,
                'credit_assigned_to': False,
            })

            order.message_post(
                body=_(
                    "🔄 Credit approval process has been reset by %s. Please submit again for approval.") % self.env.user.name
            )

    def _update_credit_assigned_to(self, send_notification=True):
        for rec in self:
            next_user = None
            for line in sorted(rec.credit_approval_users_ids, key=lambda x: x.sequence):
                if not line.state:
                    next_user = line.user_id
                    break
            rec.credit_assigned_to = next_user

            if rec.credit_assigned_to:
                rec._create_payment_term_activity_and_send_notification(send_notification)

    def _update_state_based_on_approvals(self):
        """Called from payment.term.approval.users to update boolean fields."""
        for rec in self:
            states = rec.credit_approval_users_ids.mapped('state')
            if any(s == 'reject' for s in states):
                rec.is_payment_rejected = True
                rec.is_pending_approval = False
                rec.is_payment_approved = False
            elif states and all(s == 'approve' for s in states):
                rec.is_payment_approved = True
                rec.is_pending_approval = False
                rec.is_payment_rejected = False

    def _create_payment_term_activity_and_send_notification(self, send_notification=True):
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'Payment Credit approval for: {rec.name}',
                note=_("You have been assigned to review this Payment Term Credit approval."),
                user_id=rec.credit_assigned_to.id,
                date_deadline=fields.Date.context_today(self),
            )

            if send_notification:
                rec.env['bus.bus']._sendone(
                    rec.credit_assigned_to.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': _("Credit Payment Term approval for %s") % rec.name,
                        'message': _("Activity assigned to you."),
                        'sticky': True,
                    },
                )

                if self.env.user.partner_id != rec.credit_assigned_to.partner_id:
                    rec.env['bus.bus']._sendone(
                        self.env.user.partner_id,
                        'simple_notification',
                        {
                            'type': 'info',
                            'title': f"Credit Payment Term '{rec.name}' successfully submitted for approval",
                            'message': "",
                            'sticky': True,
                        },
                    )


class PaymentTermApprovalUsers(models.Model):
    _name = "payment.term.approval.users"
    _rec_name = 'payment_approval_id'
    _description = "Approval Users"
    _order = "sequence"

    sequence = fields.Integer(string='Sequence')
    payment_approval_id = fields.Many2one('sale.order', string="Payment Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected'),('suspended', 'Suspended'),('reset', 'Reset'), ], string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.payment_approval_id:
                rec.payment_approval_id._update_state_based_on_approvals()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super(PaymentTermApprovalUsers, self).create(vals_list)
        for res in res_list:
            if res.payment_approval_id:
                res.payment_approval_id._update_state_based_on_approvals()
        return res_list
