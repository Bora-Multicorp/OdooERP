# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderCancellationApproval(models.Model):
    _inherit = 'sale.order'

    old_state = fields.Char()
    so_assigned_to_form_cancellation = fields.Many2one('res.users', string='Assigned To', tracking=True)
    so_approval_users_ids_for_cancellation = fields.One2many('so.cancellation.approval.users',
                                                          'so_cancellation_approval_id',
                                                          'Cancellation SO Approval Authorities',
                                                          help='SO cancellation approval authority details')

    def assign_cancel_users(self, so_cancellation_approval_users):

        so_cancel_approval_user_vals = []
        for index, approval in  enumerate(so_cancellation_approval_users):
            so_cancel_approval_user_vals.append((0, 0, {
                'sequence': index +1,
                'user_id': approval.user_id.id,
            }))
        self.write({
            'so_approval_users_ids_for_cancellation': so_cancel_approval_user_vals,
            'old_state': self.state,
            'state': 'cancellation_pending'
        })

        if self.id:
            self._update_assigned_to_form_SO_cancellation()

        self._create_activity_and_send_notification_for_cancel_request()

    def action_cancel(self):
        so_cancellation_approval_users = self.env['sale.order.cancellation.approvers'].sudo().search([])
        if not so_cancellation_approval_users:
            raise ValidationError("Please add cancellation authority before submit request.")
        if self.so_assigned_to_form_cancellation:
            for user_id in self.so_approval_users_ids_for_cancellation:
                if user_id.state == 'reject':
                    raise ValidationError(
                        f"Cancellation request is rejected by '{user_id.user_id.name}', please review 'Cancellation Approval Authorities' tab for more details.")
            raise ValidationError(
                f"Cancellation request is now pending from '{self.so_assigned_to_form_confirmation.name}'.")

        return self.env.ref(
            "bora_sale_purchase_approval.action_cancelation_approval_user_picker_wizard"
        ).sudo().read()[0]


    def _update_assigned_to_form_SO_cancellation(self):
        for rec in self:
            next_user = None
            last_user_approval_state = ''
            for line in sorted(rec.so_approval_users_ids_for_cancellation, key=lambda x: x.sequence):
                last_user_approval_state = line.state
                if not line.state:
                    next_user = line.user_id
                    break
            rec.so_assigned_to_form_cancellation = next_user

            if not rec.so_assigned_to_form_cancellation:
                if last_user_approval_state == 'suspended' or last_user_approval_state == 'reject':
                    self.write({
                        'state': self.old_state
                    })
                else:
                    super(SaleOrderCancellationApproval, self).action_cancel()
                    self.write({
                        'state': 'cancel'
                    })


    def _send_notification_on_rejection_of_SO_cancellation(self):

        approval_users = self.env['sale.order.cancellation.approvers'].sudo().search([])

        self.write({
            'so_assigned_to_form_confirmation': None
        })

        for user in approval_users:
            if user.user_id == self.env.user:
                self.env['bus.bus']._sendone(
                    user.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f'SO cancel approval request for {self.name}, successfully rejected by you.',
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
                        'title': f'SO cancel approval request for {self.name}, rejected by {self.env.user.name}.',
                        'message': f'',
                        'sticky': True,
                    },
                )


    def _create_activity_and_send_notification_on_cancellation_approval(self):

        for rec in self:

            if not rec.so_assigned_to_form_cancellation:
                rec.env['bus.bus']._sendone(
                    rec.create_uid.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'SO {rec.name} successfully cancelled by approver, you can now proceed further.',
                        'message': '',
                        'sticky': True,
                    },
                )

            else:

                # 1. schedule activity for next assignee
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=f'SO {rec.name} cancel approval request assigned to you.',
                    note="You have been assigned to cancel this SO.",
                    user_id=rec.so_assigned_to_form_cancellation.id,
                    date_deadline=fields.Date.context_today(self),
                )

                # 2. send notification to next approver
                rec.env['bus.bus']._sendone(
                    rec.so_assigned_to_form_cancellation.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'SO cancellation approval request for {rec.name}, assigned to you.',
                        'message': 'You have been assigned to cancel this SO.',
                        'sticky': True,
                    },
                )

            # 4. in the last send info message to self
            rec.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': f'SO cancellation approval request successfully submitted by you.',
                    'message': '',
                    'sticky': True,
                },
            )

    def _create_activity_and_send_notification_for_cancel_request(self):
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'SO cancel approval for order: {rec.name}',
                note="You have been assigned to cancel this SO.",
                user_id=rec.so_assigned_to_form_cancellation.id,
                date_deadline=fields.Date.context_today(self),
            )

            rec.env['bus.bus']._sendone(
                rec.so_assigned_to_form_cancellation.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': f'SO cancel approval request for {rec.name}, assigned to you.',
                    'message': f'Activity assigned to you.',
                    'sticky': True,
                },
            )

            if rec.so_assigned_to_form_cancellation.partner_id != self.env.user.partner_id:
                rec.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f'SO {rec.name} cancel approval request sent successfully.',
                        'message': '',
                        'sticky': True,
                    },
                )

    def action_so_suspend(self):
        return self.env.ref(
            "bora_sale_purchase_approval.cnacel_suspend_so_confirm_wizard_action"
        ).sudo().read()[0]

    def suspend_so_cancelation_process(self, remark):

        self.message_post(
            body=f"Approval suspended by {self.env.user.display_name}. Reason: {remark}",
            message_type="comment",
            subtype_xmlid="mail.mt_note"
        )
        
        for order in self:
            pending_approvers = order.so_approval_users_ids_for_cancellation.filtered(lambda u: not u.state)

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

            order.write({'so_assigned_to_form_cancellation': None, 'state': self.old_state})

            # send notification to creator
            order.env['bus.bus']._sendone(
                order.create_uid.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': f'SO {order.name} cancellation suspended by {self.env.user.name}. you need to initiate the approval process again.',
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
                    'title': f'Cancellation process suspended successfully.',
                    'message': '',
                    'sticky': True,
                },
            )

            activities.unlink()


class SOCancellationApprovalUsers(models.Model):
    _name = "so.cancellation.approval.users"
    _rec_name = 'so_cancellation_approval_id'
    _description = "SO Cancellation Approval Users"
    _order = "create_date, sequence"

    sequence = fields.Integer(string='Sequence')
    so_cancellation_approval_id = fields.Many2one('sale.order', string="SO Cancellation Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected'), ('suspended', 'Suspended')],
                             string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")