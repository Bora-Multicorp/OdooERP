from odoo import fields, models, api
from odoo.exceptions import ValidationError 

class PurchaseOrderUnlock(models.Model):
    _inherit = 'purchase.order'

    assigned_to = fields.Many2one('res.users', string='Assigned To')
    approval_users_ids = fields.One2many('po.unlock.approval.users', 'po_unlock_approval_id', 'Unlock Approval Authorities', help='PO unlock approval authority details')
    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_users', store=True)
    

    @api.depends('approval_users_ids.user_id') 
    def _compute_existing_users(self):
        for record in self:
            if record.approval_users_ids:
                record.existing_user_ids = [(6, 0, record.approval_users_ids.mapped('user_id').ids)]
            else:
                record.existing_user_ids = [(6, 0, [])]


    def assign_unlock_users(self, po_confirm_approval_users):
        super(PurchaseOrderUnlock, self).button_confirm()

        po_unlock_approval_user_vals = []
        for index,approval in enumerate(po_confirm_approval_users):
            po_unlock_approval_user_vals.append((0, 0, {
                'sequence': index+1,
                'user_id': approval.user_id.id,
            }))
        self.write({
            'approval_users_ids': po_unlock_approval_user_vals,
            'state': 'done'
        })

        

        if self.id:
            self._update_assigned_to_For_unlock()

        self._create_activity_and_send_notification_for_unlock_request()


    def button_unlock(self):
 
        # 1. Check if the authority configured or not
        po_unlock_approval_users = self.env['purchase.order.approvers'].sudo().search([])
        if not po_unlock_approval_users:
            raise ValidationError("Please add unlock authority before submit request.")


        # 2. Check if request is pending 
        if self.assigned_to:
            raise ValidationError(f"Unlock request is now pending from '{self.assigned_to.name}'.")

        # 3. Show picker
        return self.env.ref(
            "bora_purchase.action_unlock_approval_user_picker_wizard"
        ).sudo().read()[0]


    def action_unlock_suspend(self):
        return self.env.ref(
            "bora_purchase.unlock_suspend_po_confirm_wizard_action"
        ).sudo().read()[0]


    def suspend_unlock_process(self, remark):

        self.message_post(
            body=f"Unlock approval suspended by {self.env.user.display_name}. Reason: {remark}",
            message_type="comment",
            subtype_xmlid="mail.mt_note"
        )

        for order in self:

            pending_approvers = order.approval_users_ids.filtered(lambda u: not u.state)

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

            order.write({'assigned_to': None, 'state':'done'}) 

            # send notification to creator
            order.env['bus.bus']._sendone(
                order.create_uid.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': f'PO {order.name} suspended by {self.env.user.name}. you need to initiate the approval process again.',
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
                    'title': f'Approval process suspended successfully.',
                    'message':  '',
                    'sticky': True,
                },
            )


            activities.unlink()

    def _update_assigned_to_For_unlock(self):
        for rec in self:
            next_user = None
            for line in sorted(rec.approval_users_ids, key=lambda x: x.sequence):
                if not line.state:
                    next_user = line.user_id
                    break
            rec.assigned_to = next_user

            if not rec.assigned_to:
                super(PurchaseOrderUnlock, self).button_unlock()
                rec.state = 'draft'

    def _send_notification_on_rejection(self):
        
        approval_users = self.env['purchase.order.approvers'].sudo().search([])

        self.write({
            'state': 'done',
            'assigned_to': None
        })

        for user in approval_users:
            if user.user_id == self.env.user: 
                self.env['bus.bus']._sendone(
                    user.user_id.partner_id,
                    'simple_notification', 
                    {
                        'type': 'info',
                        'title': f'PO unlock approval request for {self.name}, successfully rejected by you.',
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
                        'title': f'PO unlock approval request for {self.name}, rejected by {self.env.user.name}.',
                        'message':  f'',
                        'sticky': True,
                    },
                )

    def _create_activity_and_send_notification_on_approval(self):

        for rec in self:

            if not rec.assigned_to:
                # 1. send unlock notification to real creator
                rec.env['bus.bus']._sendone(
                    rec.create_uid.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'PO {rec.name} successfully unlocked by approver, you can make changes now.',
                        'message':  '',
                        'sticky': True,
                    },
                )

            else:

                # 1. schedule activity for next assignee 
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=f'PO {rec.name} unlock approval request assigned to you.',
                    note="You have been assigned to unlock this PO.",
                    user_id=rec.assigned_to.id,
                    date_deadline=fields.Date.context_today(self),
                )

                # 2. send notification to next approver
                rec.env['bus.bus']._sendone(
                    rec.assigned_to.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'PO unlock approval request for {rec.name}, assigned to you.',
                        'message':  f'Activity assigned to you.',
                        'sticky': True,
                    },
                )




            #. in the last send info message to self
            rec.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': f'PO unlock request successfully submitted by you.',
                    'message':  '',
                    'sticky': True,
                },
            )

    def _create_activity_and_send_notification_for_unlock_request(self):
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'PO unlock approval for order: {rec.name}',
                note="You have been assigned to unlock this PO.",
                user_id=rec.assigned_to.id,
                date_deadline=fields.Date.context_today(self),
            )

            rec.env['bus.bus']._sendone(
                rec.assigned_to.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': f'PO unlock approval request for {rec.name}, assigned to you.',
                    'message':  f'Activity assigned to you.',
                    'sticky': True,
                },
            )

            if rec.assigned_to.partner_id != self.env.user.partner_id:
                rec.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': 'info',
                        'title': f'PO {rec.name} unlock approval request sent successfully.',
                        'message':  '',
                        'sticky': True,
                    },
                )

 


class POUnlockApprovalUsers(models.Model):
    _name = "po.unlock.approval.users"
    _rec_name = 'po_unlock_approval_id'
    _description = "PO Unlock Approval Users"
    _order = "create_date, sequence"

    sequence = fields.Integer(string='Sequence')
    po_unlock_approval_id = fields.Many2one('purchase.order', string="O Unlock Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected'), ('suspended', 'Suspended')], string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")