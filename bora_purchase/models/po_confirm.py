from odoo import fields, models, api
from odoo.exceptions import ValidationError 

class PurchaseOrderConfirmApproval(models.Model):
    _inherit = 'purchase.order'

    assigned_to_form_confirmation = fields.Many2one('res.users', string='Assigned To')
    approval_users_ids = fields.One2many('po.confirm.approval.users', 'po_confirm_approval_id', 'Confirm PO Approval Authorities', help='PO confirm approval authority details')
    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_users', store=True)
    

    @api.depends('approval_users_ids.user_id') 
    def _compute_existing_users(self):
        for record in self:
            if record.approval_users_ids:
                record.existing_user_ids = [(6, 0, record.approval_users_ids.mapped('user_id').ids)]
            else:
                record.existing_user_ids = [(6, 0, [])]


    # show_unlock_approve_reject_buttons = fields.Boolean(string="Show", compute='_show_approve_reject_buttons', store=False)

    # @api.depends('assigned_to','approval_users_ids.state')
    # def _show_approve_reject_buttons(self):

    #     # check if any user has rejected the request
    #     is_rejected = False
    #     for user_id in self.approval_users_ids:
    #         if user_id.state == 'reject':
    #             is_rejected = True
    #             break

    #     # check if all users have approved
    #     do_all_approve = True
    #     for user_id in self.approval_users_ids:
    #         if not user_id.state:
    #             do_all_approve = False

    #     if do_all_approve == True or is_rejected == True:
    #         self.show_unlock_approve_reject_buttons = False
    #     elif self.assigned_to == self.env.user:
    #         self.show_unlock_approve_reject_buttons = True
    #     else:
    #         self.show_unlock_approve_reject_buttons = False


    def button_confirm(self):

        po_confirm_approval_users = self.env['purchase.order.approvers'].sudo().search([])
        if not po_confirm_approval_users:
            raise ValidationError("Please add PO authority before submit request.")


        po_confirm_approval_user_vals = []
        for approval in po_confirm_approval_users:
            po_confirm_approval_user_vals.append((0, 0, {
                'sequence': approval.sequence,
                'user_id': approval.user_id.id,
            }))
        self.write({
            'approval_users_ids': po_confirm_approval_user_vals
        })


        
        if self.assigned_to_form_confirmation:
            for user_id in self.approval_users_ids:
                if user_id.state == 'reject':
                    raise ValidationError(f"PO confirm request is rejected by '{user_id.user_id.name}', please review 'PO Confirm Approval Authorities' tab for more details.")                
            raise ValidationError(f"PO confirm request is now pending from '{self.assigned_to_form_confirmation.name}'.")
        

        if self.id:
            self._update_assigned_to_form_PO_confirm()

        self._create_activity_and_send_notification_for_unlock_request()

    def _update_assigned_to_form_PO_confirm(self):
        for rec in self:
            next_user = None
            for line in sorted(rec.approval_users_ids, key=lambda x: x.sequence):
                if not line.state:
                    next_user = line.user_id
                    break
            rec.assigned_to_form_confirmation = next_user

            if not rec.assigned_to_form_confirmation:
                super(PurchaseOrderConfirmApproval, self).button_confirm()
                # rec.state = 'draft'

    def _send_notification_on_rejection(self):
        
        approval_users = self.env['purchase.order.approvers'].sudo().search([])

        for user in approval_users:
            if user.user_id == self.env.user:
                self.env['bus.bus']._sendone(
                    user.user_id.partner_id,
                    'simple_notification', 
                    {
                        'type': 'info',
                        'title': f'PO confirm approval request for {self.name}, successfully rejected by you.',
                        'message':  f'',
                        'sticky': True,
                    },
                )
            else:
                self.env['bus.bus']._sendone(
                    user.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f'PO confirm approval request for {self.name}, rejected by {self.env.user.name}.',
                        'message':  f'',
                        'sticky': True,
                    },
                )

    def _create_activity_and_send_notification_on_confirm_approval(self):

        for rec in self:

            if not rec.assigned_to_form_confirmation:
                # 1. send PO confirm notification to real creator
                rec.env['bus.bus']._sendone(
                    rec.create_uid.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'PO {rec.name} successfully confirmed by approver, you can now proceed further.',
                        'message':  '',
                        'sticky': True,
                    },
                )

            else:

                # 1. schedule activity for next assignee 
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=f'PO {rec.name} confirm approval request assigned to you.',
                    note="You have been assigned to confirm this PO.",
                    user_id=rec.assigned_to_form_confirmation.id,
                    date_deadline=fields.Date.context_today(self),
                )

                # 2. send notification to next approver
                rec.env['bus.bus']._sendone(
                    rec.assigned_to_form_confirmation.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'PO confirm approval request for {rec.name}, assigned to you.',
                        'message':  'You have been assigned to confirm this PO.',
                        'sticky': True,
                    },
                )


            #4. in the last send info message to self
            rec.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': f'PO confirm aapproval request successfully submitted by you.',
                    'message':  '',
                    'sticky': True,
                },
            )

    def _create_activity_and_send_notification_for_confirm_request(self):
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'PO confirm approval for order: {rec.name}',
                note="You have been assigned to confirm this PO.",
                user_id=rec.assigned_to_form_confirmation.id,
                date_deadline=fields.Date.context_today(self),
            )

            rec.env['bus.bus']._sendone(
                rec.assigned_to_form_confirmation.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': f'PO confirm approval request for {rec.name}, assigned to you.',
                    'message':  f'Activity assigned to you.',
                    'sticky': True,
                },
            )

            if rec.assigned_to_form_confirmation.partner_id != self.env.user.partner_id:
                rec.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f'PO {rec.name} confirm approval request sent successfully.',
                        'message':  '',
                        'sticky': True,
                    },
                )

 


class POConfirmApprovalUsers(models.Model):
    _name = "po.confirm.approval.users"
    _rec_name = 'po_confirm_approval_id'
    _description = "PO Confirm Approval Users"
    _order = "create_date, sequence"

    sequence = fields.Integer(string='Sequence')
    po_confirm_approval_id = fields.Many2one('purchase.order', string="PO Confirm Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected')], string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")