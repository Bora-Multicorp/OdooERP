from odoo import fields, models, api
from odoo.exceptions import ValidationError 

class SaleOrderUnlock(models.Model):
    _inherit = 'sale.order'

    assigned_to = fields.Many2one('res.users', string='Assigned To')
    approval_users_ids = fields.One2many('pi.unlock.approval.users', 'pi_unlock_approval_id', 'Approval Authorities', help='PI unlock approval authority details')
    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_users', store=True)
    

    @api.depends('approval_users_ids.user_id')
    def _compute_existing_users(self):
        for record in self:
            if record.approval_users_ids:
                record.existing_user_ids = [(6, 0, record.approval_users_ids.mapped('user_id').ids)]
            else:
                record.existing_user_ids = [(6, 0, [])]

    def _update_state_based_on_approvals(self):
        print('_update_state_based_on_approvals', self.approval_users_ids)


    show_unlock_approve_reject_buttons = fields.Boolean(string="Show", compute='_show_approve_reject_buttons', store=False)

    @api.depends('assigned_to','approval_users_ids.state')
    def _show_approve_reject_buttons(self):

        # check if any user has rejected the request
        is_rejected = False
        for user_id in self.approval_users_ids:
            if user_id.state == 'reject':
                is_rejected = True
                break

        # check if all users have approved
        do_all_approve = True
        for user_id in self.approval_users_ids:
            if not user_id.state:
                do_all_approve = False

        if do_all_approve == True or is_rejected == True:
            self.show_unlock_approve_reject_buttons = False
        elif self.assigned_to == self.env.user:
            self.show_unlock_approve_reject_buttons = True
        else:
            self.show_unlock_approve_reject_buttons = False

    def assign_unlock_users(self, pi_unlock_approval_users):
        pi_unlock_approval_user_vals = []
        for approval in pi_unlock_approval_users:
            pi_unlock_approval_user_vals.append((0, 0, {
                'sequence': approval.sequence,
                'user_id': approval.user_id.id,
            }))
        self.write({
            'approval_users_ids': pi_unlock_approval_user_vals
        })


        
        if self.assigned_to:
            for user_id in self.approval_users_ids:
                if user_id.state == 'reject':
                    raise ValidationError(f"Unlock request is rejected by '{user_id.user_id.name}', please review 'Unlock Approval Authorities' tab for more details.")                
            raise ValidationError(f"Unlock request is now pending from '{self.assigned_to.name}'.")
        

        if self.id:
            self._update_assigned_to()

        self._create_activity_and_send_notification_for_unlock_request()


    def action_unlock(self):

        pi_unlock_approval_users = self.env['pi.unlock.approvers'].sudo().search([])
        if not pi_unlock_approval_users:
            raise ValidationError("Please Add PI Unlock Authority before Submit Request.")

        return self.env.ref(
            "bora_sale.action_so_unlock_approval_user_picker_wizard"
        ).sudo().read()[0]

    def action_unlock_suspend(self):
        return self.env.ref(
            "bora_sale.unlock_so_suspend_confirm_wizard_action"
        ).sudo().read()[0]


    def suspend_unlock_process(self, remark):

        for order in self:

            pending_approvers = order.approval_users_ids.filtered(lambda u: not u.state)

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

            order.write({'assigned_to': None, 'state':'sale'}) 

            # send notification to creator
            order.env['bus.bus']._sendone(
                order.create_uid.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': f'SO {order.name} suspended by {self.env.user.name}. you need to initiate the approval process again.',
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



    def _update_assigned_to(self):
        for rec in self:
            next_user = None
            for line in sorted(rec.approval_users_ids, key=lambda x: x.sequence):
                if not line.state:
                    next_user = line.user_id
                    break
            rec.assigned_to = next_user

            if not rec.assigned_to:
                super(SaleOrderUnlock, self).action_unlock()
                rec.state = 'draft'

    def _send_notification_on_rejection(self):
        
        approval_users = self.env['pi.unlock.approvers'].sudo().search([])

        for user in approval_users:
            if user.user_id == self.env.user:
                self.env['bus.bus']._sendone(
                    user.user_id.partner_id,
                    'simple_notification', 
                    {
                        'type': 'info',
                        'title': f'PI unlock approval request for {self.name}, successfully rejected by you.',
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
                        'title': f'PI unlock approval request for {self.name}, rejected by {self.env.user.name}.',
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
                        'title': f'PI {rec.name} successfully unlocked by approver, you can make changes now.',
                        'message':  '',
                        'sticky': True,
                    },
                )

            else:

                # 1. schedule activity for next assignee 
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=f'PI {rec.name} unlock approval request assigned to you.',
                    note="You have been assigned to unlock this PI.",
                    user_id=rec.assigned_to.id,
                    date_deadline=fields.Date.context_today(self),
                )

                # 2. send notification to next approver
                rec.env['bus.bus']._sendone(
                    rec.assigned_to.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': f'PI unlock approval request for {rec.name}, assigned to you.',
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
                    'title': f'PI unlock request successfully submitted by you.',
                    'message':  '',
                    'sticky': True,
                },
            )

    def _create_activity_and_send_notification_for_unlock_request(self):
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'PI unlock approval for sale order: {rec.name}',
                note="You have been assigned to unlock this PI.",
                user_id=rec.assigned_to.id,
                date_deadline=fields.Date.context_today(self),
            )

            rec.env['bus.bus']._sendone(
                rec.assigned_to.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': f'PI unlock approval request for {rec.name}, assigned to you.',
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
                        'title': f'PI {rec.name} unlock approval request sent successfully.',
                        'message':  '',
                        'sticky': True,
                    },
                )




class PIUnlockApprovalUsers(models.Model):
    _name = "pi.unlock.approval.users"
    _rec_name = 'pi_unlock_approval_id'
    _description = "PI Unlock Approval Users"
    _order = "create_date, sequence"

    sequence = fields.Integer(string='Sequence')
    pi_unlock_approval_id = fields.Many2one('sale.order', string="PI Unlock Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected'), ('suspended', 'Suspended')], string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.pi_unlock_approval_id:
                rec.pi_unlock_approval_id._update_state_based_on_approvals()
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
        res_list = super(PIUnlockApprovalUsers, self).create(vals_list)
        for res in res_list:
            if res.pi_unlock_approval_id:
                res.pi_unlock_approval_id._update_state_based_on_approvals()
        return res_list
