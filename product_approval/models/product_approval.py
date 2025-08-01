import logging
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError 
from lxml import etree
_logger = logging.getLogger(__name__)


class ProductApproval(models.Model): 
    _inherit = 'product.template'
    _description ='Product Approval Queue'

    is_hidden_for_approval = fields.Boolean(default=False) 

    is_approved = fields.Boolean(string='Is Approved', default=False, help="Indicates if the product has been approved.")

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        product_approval_users = self.env['product.approval.config'].sudo().search([])

        if product_approval_users:
            approval_user_vals = []
            for approval in product_approval_users:
                approval_user_vals.append((0, 0, {
                    'sequence': approval.sequence,
                    'user_id': approval.user_id.id,
                }))
            defaults['approval_users_ids'] = approval_user_vals
        return defaults

    # product_id = fields.Many2one('product.template', string="Product")

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected')
    ], default='draft', string='Status', tracking=True)

    approval_users_ids = fields.One2many('product.approval.users', 'product_approval_id', 'Approval Authorities',
                                         help='Approval Authority Details')
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_users', store=True)


    # @api.depends('existing_user_ids.user_id')
    # def _compute_approval_user_ids(self):
    #     for record in self:
    #         # Get the user_ids from related approval_detail_ids
    #         user_ids = record.existing_user_ids.mapped('user_id')
    #         # Assign the collected users to approval_user_ids
    #         record.existing_user_ids = [(6, 0, user_ids.ids)]


    @api.depends('approval_users_ids.user_id')
    def _compute_existing_users(self):
        for record in self:
            if record.approval_users_ids:
                record.existing_user_ids = [(6, 0, record.approval_users_ids.mapped('user_id').ids)]
            else:
                record.existing_user_ids = [(6, 0, [])]


    def action_unarchive(self):
        for record in self:
            if record.is_hidden_for_approval:
                raise UserError("This product cannot be unarchived because it is under approval process.")
        return super(ProductApproval, self).action_unarchive()

    def confirm_submit_form(self):
        if not self.approval_users_ids:
            raise ValidationError(_("Please Add Approval Authority before Submit Request."))

        if self.id:
            self.write({'state': 'pending'})
            self._update_assigned_to()

    def approve_by_manager(self):
        self.write({'state': 'confirmed'})

    def _update_assigned_to(self):
        for rec in self:
            next_user = None
            for line in sorted(rec.approval_users_ids, key=lambda x: x.sequence):
                if not line.state:
                    next_user = line.user_id
                    break
            rec.assigned_to = next_user

            if rec.assigned_to:
                rec._create_activity_and_send_notification()
            

    def _update_state_based_on_approvals(self):
        for rec in self:
            states = rec.approval_users_ids.mapped('state')
            if any(s == 'reject' for s in states):
                rec.state = 'rejected'
            elif states and all(s == 'approve' for s in states):
                rec.state = 'confirmed'

    domain_field = fields.Char(compute='_compute_domain')
    
    @api.depends('state')
    def _compute_domain(self):
        for rec in self:
            if rec.state == 'draft':
                rec.domain_field = "[('active', '=', False), ('is_hidden_for_approval', '=', True), '|', ('create_uid', '=', uid)]"
            else:
                rec.domain_field = "[('active', '=', False), ('is_hidden_for_approval', '=', True)]"




    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['is_hidden_for_approval'] = True
            vals['active'] = False  # Archive product by default

        templates = super(ProductApproval, self).create(vals_list)
        for template in templates:
            template.product_variant_ids.write({
                'active': False,
                # 'is_hidden_for_approval': True,
            })

        return templates
    
    def _create_activity_and_send_notification(self):
        # Schedule activity to assign to user
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'Product approval for: {rec.name}',
                note=_("You have been assigned to review this product approval."),
                user_id=rec.assigned_to.id,
                date_deadline=fields.Date.context_today(self),
            )

            rec.env['bus.bus']._sendone(
                rec.assigned_to.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': _("Product approval for %s") % rec.name,
                    'message':  _("Activity assigned to you."),
                    'sticky': True,
                },
            )

    
    def write(self, vals):
        res = super().write(vals)

        def _schedule_activity(record, user1, title, note):
            record.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=title,
                note=note,
                user_id=user1.id,
                date_deadline=fields.Date.context_today(record),
            )

        def _send_notification(record, user1, title, message, type='success'):
            record.env['bus.bus']._sendone(
                user1.partner_id,
                'simple_notification',
                {
                    'type': type,
                    'title': title,
                    'message': message,
                    'sticky': True,
                },
            )

        for record in self:
            if vals.get('state') == 'confirmed':

                for record in self:
                    record.write({'active': True})
                    for variant in record.product_variant_ids:
                        variant.write({
                            'active': True,
                            # 'is_hidden_for_approval': True,
                        })



                    # Send approval activity and notification
                    for user in record.approval_users_ids:
                        user1 = user.user_id
                        _schedule_activity(
                            record, user1,
                            title=f"Product '{record.name}' is approved.",
                            note=_(
                                "Product '%s' has been approved. Please take necessary follow-up action.") % record.name
                        )
                        _send_notification(
                            record, user1,
                            title=f"Product '{record.name}' is approved.",
                            message=_(
                                "Product '%s' has been approved. Please check the system for further details.") % record.name
                        )

            elif vals.get('state') == 'rejected':

                for user in record.approval_users_ids:
                    user1 = user.user_id
                    _schedule_activity(
                        record, user1,
                        title=f"Product '{record.name}' is rejected.",
                        note=_("Product '%s' has been rejected. Please take necessary action.") % record.name
                    )
                    _send_notification(
                        record, user1,
                        title=f"Product '{record.name}' is rejected.",
                        message=_(
                            "Product '%s' has been rejected. Please check the system for more details.") % record.name,
                        type='danger'
                    )

        if not self.active:
            for variant_id in self.product_variant_ids:
                variant_id.write({
                    'active': False,
                    # 'is_hidden_for_approval': True,
                })

        return res



class ProductApprovalUsers(models.Model):
    _name = "product.approval.users"
    _rec_name = 'product_approval_id'
    _description = "Approval Users"
    _order = "sequence"

    sequence = fields.Integer(string='Sequence')
    product_approval_id = fields.Many2one('product.template', string="Product Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected')], string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.product_approval_id:
                rec.product_approval_id._update_state_based_on_approvals()
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
        res_list = super(ProductApprovalUsers, self).create(vals_list)
        for res in res_list:
            if res.product_approval_id:
                res.product_approval_id._update_state_based_on_approvals()
        return res_list