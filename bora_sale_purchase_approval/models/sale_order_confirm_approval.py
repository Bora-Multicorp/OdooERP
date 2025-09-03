# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrderConfimationApproval(models.Model):
    _inherit = 'sale.order'
    _description = 'Sales Order Approval Queue'

    is_hidden_for_approval = fields.Boolean(default=False)
    is_approved = fields.Boolean(string='Is Approved', default=False,
                                 help="Indicates if the sales order has been approved.")

    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_users', store=True)

    state = fields.Selection([
            ('custom_draft', 'Draft'),
            ('confirmation_pending', 'Confirmation Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('draft', 'Quotation'),
            ('sent', 'Quotation Sent'),
            ('sale', 'Sales Order'),
            ('done', 'Locked'),
            ('cancel', 'Cancelled')],
        string="Status",
        default="custom_draft",   # ✅ set your custom default state
        tracking=True
    )

    confirm_approval_users_ids = fields.One2many('sale.order.approval.users', 'sale_order_id', 'Approval Authorities',
                                         help='Approval Authority Details')
    assigned_to = fields.Many2one('res.users', string='Assigned To')



    # @api.model
    # def create(self, vals):
    #     if not vals.get("state"):
    #         vals["state"] = "custom_draft"
    #     return super(SaleOrderConfimationApproval, self).create(vals)

    def action_draft_confirm(self):
        """
        Overrides the standard action_confirm. If approval is needed, it triggers the approval flow.
        """
        self.ensure_one()

        # bring approval users here instead of default_get
        if not self.confirm_approval_users_ids:
            approval_config_users = self.env['sale.order.approval.config'].sudo().search([])
            if approval_config_users:
                approval_user_vals = []
                for approval in approval_config_users:
                    approval_user_vals.append((0, 0, {
                        'sequence': approval.sequence,
                        'user_id': approval.user_id.id,
                    }))
                self.write({'confirm_approval_users_ids': approval_user_vals})

        if self.state == 'custom_draft':
            if not self.confirm_approval_users_ids:
                raise ValidationError(_("Please add Approval Authority before submitting the request."))
            self.write({'state': 'confirmation_pending', 'is_hidden_for_approval': True})
            self._update_assigned_to()
            return

        # Call the original Odoo method if approval isn't needed
        return super(SaleOrderConfimationApproval, self).action_confirm()



    @api.depends('confirm_approval_users_ids.user_id')
    def _compute_existing_users(self):
        """Computes the list of existing users in the approval chain."""
        for record in self:
            if record.confirm_approval_users_ids:
                record.existing_user_ids = [(6, 0, record.confirm_approval_users_ids.mapped('user_id').ids)]
            else:
                record.existing_user_ids = [(6, 0, [])]


    def _update_assigned_to(self, send_notification=True):
        for rec in self:
            next_user = None
            for line in sorted(rec.confirm_approval_users_ids, key=lambda x: x.sequence):
                if not line.state:
                    next_user = line.user_id
                    break
            rec.assigned_to = next_user

            if rec.assigned_to:
                rec._create_confirm_sale_order_activity_and_send_notification(send_notification)

    def _update_state_based_on_approvals(self):
        for rec in self:
            states = rec.confirm_approval_users_ids.mapped('state')
            if any(s == 'reject' for s in states):
                rec.state = 'rejected'
            elif states and all(s == 'approve' for s in states):
                rec.state = 'approved'
                rec.is_hidden_for_approval = False
                rec.is_approved = True
                rec.state = 'draft'



    domain_field = fields.Char(compute='_compute_domain')

    @api.depends('state')
    def _compute_domain(self):
        for rec in self:
            if rec.state == 'draft':
                rec.domain_field = "[('active', '=', False), ('is_hidden_for_approval', '=', True), '|', ('create_uid', '=', uid)]"
            else:
                rec.domain_field = "[('active', '=', False), ('is_hidden_for_approval', '=', True)]"

    def _create_confirm_sale_order_activity_and_send_notification(self, send_notification=True):
        """Schedules an activity and sends a notification to the assigned user."""
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'Sales Order Confirmation approval for: {rec.name}',
                note=_("You have been assigned to review this sales order Cancellation."),
                user_id=rec.assigned_to.id,
                date_deadline=fields.Date.context_today(self),
            )
            if send_notification == True:
                rec.env['bus.bus']._sendone(
                    rec.assigned_to.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': _("Sales Order Confirmation approval for %s") % rec.name,
                        'message': _("Activity assigned to you."),
                        'sticky': True,
                    },
            )


            if self.env.user.partner_id != rec.assigned_to.partner_id:
                    rec.env['bus.bus']._sendone(
                        self.env.user.partner_id,
                        'simple_notification',
                        {
                            'type': 'info',
                            'title': f"Sale Order '{rec.name}' successfully submitted for approval",
                            'message': "",
                            'sticky': True,
                        },
                    )


class SaleOrderApprovalUsers(models.Model):
    _name = "sale.order.approval.users"
    _rec_name = 'user_id'
    _description = "Sales Order Approval Users"
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
                rec.sale_order_id._update_state_based_on_approvals()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super(SaleOrderApprovalUsers, self).create(vals_list)
        for res in res_list:
            if res.sale_order_id:
                res.sale_order_id._update_state_based_on_approvals()
        return res_list
