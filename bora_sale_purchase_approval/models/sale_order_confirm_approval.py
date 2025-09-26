# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderConfimationApproval(models.Model):
    _inherit = 'sale.order'
    _description = 'Sales Order Approval Queue'

    so_assigned_to_form_confirmation = fields.Many2one('res.users', string='Assigned To', tracking=True)
    so_approval_users_ids_for_confirmation = fields.One2many('so.confirm.approval.users', 'so_confirm_approval_id',
                                                             'Confirm SO Approval Authorities',
                                                             help='SO confirm approval authority details')

    state = fields.Selection(
        [('draft', "Quotation"),
         ("confirmation_pending", "Confirmation Pending"),
         ('cancellation_pending', 'Cancellation Pending'),
         ('unlock_pending', 'Unlock Pending'),
         ('sent', "Quotation Sent"),
         ('sale', "Proforma Invoice"),
         ('cancel', "Cancelled"),
         ],
        string="Status",
        tracking=True
    )

    def _confirmation_error_message(self):
        """ Return whether order can be confirmed or not if not then returm error message. """
        self.ensure_one()
        if self.state not in {'draft', 'sent', 'confirmation_pending', 'cancellation_pending'}:
            return _("Some orders are not in a state requiring confirmation.")
        if any(
                not line.display_type
                and not line.is_downpayment
                and not line.product_id
                for line in self.order_line
        ):
            return _("A line on these orders missing a product, you cannot confirm it.")

        return False

    def assign_users(self, so_confirm_approval_users):
        # super(SaleOrderConfimationApproval, self).action_confirm()

        so_confirm_approval_user_vals = []
        for index, approval in enumerate(so_confirm_approval_users):
            so_confirm_approval_user_vals.append((0, 0, {
                'sequence': index + 1,
                'user_id': approval.user_id.id,
            }))
        self.write({
            'so_approval_users_ids_for_confirmation': so_confirm_approval_user_vals,
            'state': 'confirmation_pending'
        })

        # if self.so_assigned_to_form_confirmation:
        #     for user_id in self.so_approval_users_ids_for_confirmation:
        #         if user_id.state == 'reject':
        #             raise ValidationError(
        #                 f"PO confirm request is rejected by '{user_id.user_id.name}', please review 'PO Confirm Approval Authorities' tab for more details.")
        #     raise ValidationError(
        #         f"PO confirm request is now pending from '{self.so_assigned_to_form_confirmation.name}'.")

        if self.id:
            self._update_assigned_to_form_SO_confirm()

        self._create_activity_and_send_notification_for_confirm_request()

    # def action_confirm(self):
    #
    #     so_confirm_approval_users = self.env['sale.order.approval.config'].sudo().search([])
    #     if not so_confirm_approval_users:
    #         raise ValidationError("Please add confirmation approval authority before submit request.")
    #
    #     if self.so_assigned_to_form_confirmation:
    #         raise ValidationError(
    #             f"SO confirm request is now pending from '{self.so_assigned_to_form_confirmation.name}'.")
    #
    #     return self.env.ref(
    #         "bora_sale_purchase_approval.action_so_confirmation_approval_user_picker_wizard"
    #     ).sudo().read()[0]

    def action_confirm(self):
        for order in self:
            # === Step 1: Check credit payment approval ===
            if order.payment_term_id and order.payment_term_id.name == "Credit Payment":
                active_lines = order.credit_approval_users_ids.filtered(lambda l: l.active_cycle)

                if not active_lines:
                    raise ValidationError(
                        _("No active credit approval cycle found. Please submit the order for credit approval first.")
                    )

                states = active_lines.mapped('state')

                # If any rejected → block
                if any(s == 'reject' for s in states):
                    raise ValidationError(
                        _("This Sale Order cannot be confirmed unitl credit term approved")
                    )

                # If not all approved → block
                if any(s != 'approve' for s in states):
                    raise ValidationError(
                        _("You cannot confirm this Sale Order until all approvers approves Credit Payment Term")
                    )

                # Passed → mark as approved
                order.is_payment_approved = True

            # === Step 2: Proceed with SO confirmation approval ===
            so_confirm_approval_users = self.env['sale.order.approval.config'].sudo().search([])
            if not so_confirm_approval_users:
                raise ValidationError(_("Please add confirmation approval authority before submitting the request."))

            if order.so_assigned_to_form_confirmation:
                raise ValidationError(
                    _("SO confirm request is now pending from '%s'.") % order.so_assigned_to_form_confirmation.name
                )

        return self.env.ref(
            "bora_sale_purchase_approval.action_so_confirmation_approval_user_picker_wizard"
        ).sudo().read()[0]

    def _update_assigned_to_form_SO_confirm(self):
        for rec in self:
            next_user = None
            for line in sorted(rec.so_approval_users_ids_for_confirmation, key=lambda x: x.sequence):
                if not line.state:
                    next_user = line.user_id
                    break
            rec.so_assigned_to_form_confirmation = next_user

            if not rec.so_assigned_to_form_confirmation:
                super(SaleOrderConfimationApproval, self).action_confirm()
                self.write({
                    'state': 'sale'
                })

    def _send_notification_on_rejection_of_SO_confirmation(self):

        confirmation_approval_users = self.env['sale.order.approval.config'].sudo().search([])
        super(SaleOrderConfimationApproval, self).action_unlock()

        self.write({
            'state': 'draft',
            'so_assigned_to_form_confirmation': None
        })

        for user in confirmation_approval_users:
            if user.user_id == self.env.user:
                self.env['bus.bus']._sendone(
                    user.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f'SO confirm approval request for {self.name}, successfully rejected by you.',
                        'message': f'',
                        'sticky': True,
                    },
                )
            else:
                self.env['bus.bus']._sendone(
                    user.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'danger',
                        'title': f'SO confirm approval request for {self.name}, rejected by {self.env.user.name}.',
                        'message': f'',
                        'sticky': True,
                    },
                )

    def _create_activity_and_send_notification_on_confirm_approval(self):

        for rec in self:

            if not rec.so_assigned_to_form_confirmation:
                rec.env['bus.bus']._sendone(
                    rec.create_uid.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'SO {rec.name} successfully confirmed by approvers, you can now proceed further.',
                        'message': '',
                        'sticky': True,
                    },
                )

            else:

                # 1. schedule activity for next assignee
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=f'SO {rec.name} confirm approval request assigned to you.',
                    note="You have been assigned to confirm this SO.",
                    user_id=rec.so_assigned_to_form_confirmation.id,
                    date_deadline=fields.Date.context_today(self),
                )

                # 2. send notification to next approver
                rec.env['bus.bus']._sendone(
                    rec.so_assigned_to_form_confirmation.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'SO confirm approval request for {rec.name}, assigned to you.',
                        'message': 'You have been assigned to confirm this SO.',
                        'sticky': True,
                    },
                )

            # 4. in the last send info message to self
            rec.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': f'SO confirm approval request successfully submitted by you.',
                    'message': '',
                    'sticky': True,
                },
            )

    def _create_activity_and_send_notification_for_confirm_request(self):
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'SO confirm approval for order: {rec.name}',
                note="You have been assigned to confirm this SO.",
                user_id=rec.so_assigned_to_form_confirmation.id,
                date_deadline=fields.Date.context_today(self),
            )

            rec.env['bus.bus']._sendone(
                rec.so_assigned_to_form_confirmation.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': f'SO confirm approval request for {rec.name}, assigned to you.',
                    'message': f'Activity assigned to you.',
                    'sticky': True,
                },
            )

            if rec.so_assigned_to_form_confirmation.partner_id != self.env.user.partner_id:
                rec.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f'SO {rec.name} confirm approval request sent successfully.',
                        'message': '',
                        'sticky': True,
                    },
                )

    def action_suspend(self):
        return self.env.ref(
            "bora_sale_purchase_approval.approve_suspend_so_confirm_wizard_action"
        ).sudo().read()[0]

    def suspend_approval_process(self, remark):

        for order in self:
            pending_approvers = order.so_approval_users_ids_for_confirmation.filtered(lambda u: not u.state)

            pending_approvers.write({
                'state': 'suspended',
                'remark': f"By {self.env.user.name} - " + (f" {remark}" if remark else ""),
                'action_date': fields.Datetime.now()})

            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', self.ids),
                ('user_id', 'in', pending_approvers.mapped('user_id').ids),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ])

            order.write({'so_assigned_to_form_confirmation': None, 'state': 'draft'})

            # send notification to creator
            order.env['bus.bus']._sendone(
                order.create_uid.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': f'SO {order.name} suspended by {self.env.user.name}. you need to initiate the approval process again.',
                    'message': '',
                    'sticky': True,
                },
            )

            # 4. in the last send info message to self
            order.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': f'Approval process suspended successfully.',
                    'message': '',
                    'sticky': True,
                },
            )

            activities.unlink()


class SOConfirmApprovalUsers(models.Model):
    _name = "so.confirm.approval.users"
    _rec_name = 'so_confirm_approval_id'
    _description = "SO Confirm Approval Users"
    # _order = "create_date, sequence"

    group = fields.Selection([
        ('group1', 'Group 1'),
        ('group2', 'Group 2'),
    ], string="Groups", required=False)

    sequence = fields.Integer(string='Sequence')
    so_confirm_approval_id = fields.Many2one('sale.order', string="SO Confirm Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected'), ('suspended', 'Suspended')],
                             string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")
