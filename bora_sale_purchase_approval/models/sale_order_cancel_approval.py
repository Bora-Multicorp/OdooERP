# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderCancellationApproval(models.Model):
    _inherit = 'sale.order'

    # Cancellation approval fields
    cancel_is_hidden_for_approval = fields.Boolean(default=False)
    cancel_is_approved = fields.Boolean(string='Cancel Approved', default=False,
                                 help="Indicates if the sales order cancellation has been approved.")

    existing_user_ids = fields.Many2many('res.users', compute='_compute_cancel_existing_users', store=True)

    cancel_state = fields.Selection([
        ('cancel_draft', 'Cancel Draft'),
        ('cancel_pending', 'Waiting for Cancel Approval'),
        ('cancel_approved', 'Cancel Approved'),
        ('cancel_rejected', 'Cancel Rejected'),
    ], string="Cancel State", default='cancel_draft')

    cancel_approval_users_ids = fields.One2many(
        'sale.order.cancel.approval.users', 'sale_order_id', 'Cancel Approval Authorities',
        help='Approval Authority Details for Cancellation')
    cancel_assigned_to = fields.Many2one('res.users', string='Cancel Assigned To')

    # ========== DEFAULT APPROVERS ==========
    # @api.model
    # def default_get(self, fields_list):
    #     defaults = super().default_get(fields_list)
    #     cancel_config_users = self.env['sale.order.approval.config'].sudo().search([])
    #     if cancel_config_users:
    #         approval_user_vals = []
    #         for approval in cancel_config_users:
    #             approval_user_vals.append((0, 0, {
    #                 'sequence': approval.sequence,
    #                 'user_id': approval.user_id.id,
    #             }))
    #         defaults['cancel_approval_users_ids'] = approval_user_vals
    #     return defaults

    # ========== ACTIONS ==========
    def action_cancel_request(self):
        """
        Custom action triggered when user clicks Cancel.
        Starts the cancel approval process.
        """
        self.ensure_one()

        if self.state == 'cancel_draft':
            # If no cancel approval users already, add defaults
            if not self.cancel_approval_users_ids:
                cancel_config_users = self.env['sale.order.approval.config'].sudo().search([])
                if not cancel_config_users:
                    raise ValidationError(
                        _("Please configure Cancel Approval Authority before submitting the request."))

                approval_user_vals = []
                for approval in cancel_config_users:
                    approval_user_vals.append((0, 0, {
                        'sequence': approval.sequence,
                        'user_id': approval.user_id.id,
                    }))

                self.write({'cancel_approval_users_ids': approval_user_vals})

            # Update state and assigned_to
            self.write({
                'cancel_state': 'cancel_pending',
                'cancel_is_hidden_for_approval': True
            })
            self._update_cancel_assigned_to()
            return

        # If not in custom_draft → run default cancel flow
        return super(SaleOrderCancellationApproval, self).action_cancel()


    @api.depends('cancel_approval_users_ids.user_id')
    def _compute_cancel_existing_users(self):
        for record in self:
            if record.cancel_approval_users_ids:
                record.existing_user_ids = [(6, 0, record.cancel_approval_users_ids.mapped('user_id').ids)]
            else:
                record.existing_user_ids = [(6, 0, [])]

    def _update_cancel_assigned_to(self, send_notification=True):
        for rec in self:
            next_user = None
            for line in sorted(rec.cancel_approval_users_ids, key=lambda x: x.sequence):
                if not line.state:
                    next_user = line.user_id
                    break
            rec.cancel_assigned_to = next_user

            if rec.cancel_assigned_to:
                rec._create_cancel_sale_order_activity_and_send_notification(send_notification)

    def _update_cancel_state_based_on_approvals(self):
        for rec in self:
            states = rec.cancel_approval_users_ids.mapped('state')
            if any(s == 'reject' for s in states):
                rec.cancel_state = 'cancel_rejected'
            elif states and all(s == 'approve' for s in states):
                rec.cancel_state = 'cancel_approved'
                rec.cancel_is_hidden_for_approval = False
                # now really cancel the order
                rec.action_cancel()

    def _create_cancel_sale_order_activity_and_send_notification(self, send_notification=True):
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'Sales Order Cancellation approval for: {rec.name}',
                note=_("You have been assigned to review this sales order cancellation."),
                user_id=rec.cancel_assigned_to.id,
                date_deadline=fields.Date.context_today(self),
            )
            if send_notification:
                # Notify approver
                rec.env['bus.bus']._sendone(
                    rec.cancel_assigned_to.partner_id,
                    'simple_notification',
                    {
                        'type': 'warning',
                        'title': _("Sales Order Cancellation approval for %s") % rec.name,
                        'message': _("Activity assigned to you."),
                        'sticky': True,
                    },
                )

            # Notify requester
            if self.env.user.partner_id != rec.cancel_assigned_to.partner_id:
                rec.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f"Sale Order '{rec.name}' successfully submitted for cancellation approval",
                        'message': "",
                        'sticky': True,
                    },
                )


# ========== APPROVAL USERS FOR CANCELLATION ==========
class SaleOrderCancelApprovalUsers(models.Model):
    _name = "sale.order.cancel.approval.users"
    _rec_name = 'user_id'
    _description = "Sales Order Cancel Approval Users"
    _order = "sequence"

    sequence = fields.Integer(string='Sequence')
    sale_order_id = fields.Many2one('sale.order', string="Sales Order")
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected')], string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.sale_order_id:
                rec.sale_order_id._update_cancel_state_based_on_approvals()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super(SaleOrderCancelApprovalUsers, self).create(vals_list)
        for res in res_list:
            if res.sale_order_id:
                res.sale_order_id._update_cancel_state_based_on_approvals()
        return res_list
