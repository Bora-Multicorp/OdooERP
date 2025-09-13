from odoo import fields, models, api
from odoo.exceptions import ValidationError 

class PurchaseOrderCancellationApproval(models.Model):
    _inherit = 'purchase.order'

    old_state = fields.Char()
    assigned_to_form_cancellation = fields.Many2one('res.users', string='Assigned To', tracking=True)
    approval_users_ids_for_cancellation = fields.One2many('po.cancellation.approval.users', 'po_cancellation_approval_id', 'Cancellation PO Approval Authorities', help='PO cancellation approval authority details')

    def assign_cancel_users(self, po_cancellation_approval_users):

        po_cancel_approval_user_vals = []
        for approval in po_cancellation_approval_users:
            po_cancel_approval_user_vals.append((0, 0, {
                'sequence': approval.sequence,
                'user_id': approval.user_id.id,
            }))
        self.write({
            'approval_users_ids_for_cancellation': po_cancel_approval_user_vals,
            'old_state': self.state,
            'state': 'cancellation_pending'
        })
        
        if self.id:
            self._update_assigned_to_form_PO_cancellation()

        self._create_activity_and_send_notification_for_cancel_request()


    def button_cancel(self):

        # 1. Check if authroity is configured or not
        po_cancellation_approval_users = self.env['purchase.order.cancellation.approvers'].sudo().search([])
        if not po_cancellation_approval_users:
            raise ValidationError("Please add cancellation authority before submit request.")


        # 2. Check if any approval is pending 
        if self.assigned_to_form_cancellation:
            for user_id in self.approval_users_ids_for_cancellation:
                if user_id.state == 'reject':
                    raise ValidationError(f"Cancellation request is rejected by '{user_id.user_id.name}', please review 'Cancellation Approval Authorities' tab for more details.")
            raise ValidationError(f"Cancellation request is now pending from '{self.assigned_to_form_confirmation.name}'.")
        

        # 3. Theen show user pciker
        return self.env.ref(
            "bora_purchase.action_cancelation_approval_user_picker_wizard"
        ).sudo().read()[0]



    def _update_assigned_to_form_PO_cancellation(self):
        for rec in self:
            next_user = None
            last_user_approval_state = ''
            for line in sorted(rec.approval_users_ids_for_cancellation, key=lambda x: x.sequence):
                last_user_approval_state = line.state
                if not line.state:
                    next_user = line.user_id
                    break
            rec.assigned_to_form_cancellation = next_user


            if not rec.assigned_to_form_cancellation:
                if last_user_approval_state == 'suspended' or last_user_approval_state == 'reject':
                    self.write({
                        'state': self.old_state
                    })
                else:
                    super(PurchaseOrderCancellationApproval, self).button_cancel()



    def _send_notification_on_rejection_of_PO_cancellation(self):
        
        approval_users = self.env['purchase.order.cancellation.approvers'].sudo().search([])

        self.write({
            'assigned_to_form_confirmation': None
        })


        for user in approval_users:
            if user.user_id == self.env.user:
                self.env['bus.bus']._sendone(
                    user.user_id.partner_id,
                    'simple_notification', 
                    {
                        'type': 'info',
                        'title': f'PO cancel approval request for {self.name}, successfully rejected by you.',
                        'message':  f'',
                        'sticky': True,
                    },
                )
            else:
                self.env['bus.bus']._sendone(
                    user.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'danger',
                        'title': f'PO cancel approval request for {self.name}, rejected by {self.env.user.name}.',
                        'message':  f'',
                        'sticky': True,
                    },
                )


    def _create_activity_and_send_notification_on_cancellation_approval(self):

        for rec in self:

            if not rec.assigned_to_form_cancellation:
                # 1. send PO cancel notification to real creator
                rec.env['bus.bus']._sendone(
                    rec.create_uid.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'PO {rec.name} successfully cancelled by approver, you can now proceed further.',
                        'message':  '',
                        'sticky': True,
                    },
                )

            else:

                # 1. schedule activity for next assignee 
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=f'PO {rec.name} cancel approval request assigned to you.',
                    note="You have been assigned to cancel this PO.",
                    user_id=rec.assigned_to_form_cancellation.id,
                    date_deadline=fields.Date.context_today(self),
                )

                # 2. send notification to next approver
                rec.env['bus.bus']._sendone(
                    rec.assigned_to_form_cancellation.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'PO cancellation approval request for {rec.name}, assigned to you.',
                        'message':  'You have been assigned to cancel this PO.',
                        'sticky': True,
                    },
                )


            #4. in the last send info message to self
            rec.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': f'PO cancellation approval request successfully submitted by you.',
                    'message':  '',
                    'sticky': True,
                },
            )


    def _create_activity_and_send_notification_for_cancel_request(self):
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'PO cancel approval for order: {rec.name}',
                note="You have been assigned to cancel this PO.",
                user_id=rec.assigned_to_form_cancellation.id,
                date_deadline=fields.Date.context_today(self),
            )

            rec.env['bus.bus']._sendone(
                rec.assigned_to_form_cancellation.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': f'PO cancel approval request for {rec.name}, assigned to you.',
                    'message':  f'Activity assigned to you.',
                    'sticky': True,
                },
            )

            if rec.assigned_to_form_cancellation.partner_id != self.env.user.partner_id:
                rec.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f'PO {rec.name} cancel approval request sent successfully.',
                        'message':  '',
                        'sticky': True,
                    },
                )

    def action_suspend(self):
        return self.env.ref(
            "bora_purchase.cnacel_suspend_po_confirm_wizard_action"
        ).sudo().read()[0]

    def suspend_cancelation_process(self, remark):

        self.message_post(
            body=f"Cancellation approval suspended by {self.env.user.display_name}. Reason: {remark}",
            message_type="comment",
            subtype_xmlid="mail.mt_note"
        )

        for order in self:

            pending_approvers = order.approval_users_ids_for_cancellation.filtered(lambda u: not u.state)

            pending_approvers.write({
                'state': 'suspended', 
                'remark': f"By {self.env.user.name} - " + (f" {remark}" if remark else ""),
                'action_date': fields.Datetime.now()})

            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'purchase.order'),
                ('res_id', '=', self.ids),
                ('user_id', 'in', pending_approvers.mapped('user_id').ids),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ])

            order.write({'assigned_to_form_cancellation': None, 'state':self.old_state})

            # send notification to creator
            order.env['bus.bus']._sendone(
                order.create_uid.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': f'PO {order.name} cnacellation suspended by {self.env.user.name}. you need to initiate the approval process again.',
                    'message':  '',
                    'sticky': True,
                },
            )

            #4. in the last send info message to self
            order.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': f'Cancellation process suspended successfully.',
                    'message':  '',
                    'sticky': True,
                },
            )


            activities.unlink()


class POCancellationApprovalUsers(models.Model):
    _name = "po.cancellation.approval.users"
    _rec_name = 'po_cancellation_approval_id'
    _description = "PO Cancellation Approval Users"
    _order = "create_date, sequence"

    sequence = fields.Integer(string='Sequence')
    po_cancellation_approval_id = fields.Many2one('purchase.order', string="PO Cancellation Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected'), ('suspended', 'Suspended')], string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")