import logging
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError 
from lxml import etree
_logger = logging.getLogger(__name__)


class ProductApproval(models.Model): 
    _inherit = 'product.template'
    _description = 'Product approvals'

    is_hidden = fields.Boolean(default=False) 

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

    product_id = fields.Many2one('product.template', string="Product")


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


    @api.depends('existing_user_ids.user_id')
    def _compute_approval_user_ids(self):
        for record in self:
            # Get the user_ids from related approval_detail_ids
            user_ids = record.existing_user_ids.mapped('user_id')
            # Assign the collected users to approval_user_ids
            record.existing_user_ids = [(6, 0, user_ids.ids)]


    @api.depends('approval_users_ids.user_id')
    def _compute_existing_users(self):
        for record in self:
            if record.approval_users_ids:
                record.existing_user_ids = [(6, 0, record.approval_users_ids.mapped('user_id').ids)]
            else:
                record.existing_user_ids = [(6, 0, [])]


    def action_unarchive(self):
        for record in self:
            if record.is_hidden:
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

    def _update_state_based_on_approvals(self):
        for rec in self:
            states = rec.approval_users_ids.mapped('state')
            if any(s == 'reject' for s in states):
                rec.state = 'rejected'
            elif states and all(s == 'approve' for s in states):
                rec.state = 'confirmed'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['is_hidden'] = True
            vals['active'] = False  # Archive product by default

        templates = super(ProductApproval, self).create(vals_list)
        for template in templates:
            template.product_variant_ids.write({
                'active': False,
                # 'is_hidden': True,
            })

        return templates



    def write(self, vals):



        #     approved_to_in_vals = vals.get('assigned_to')
        #     if approved_to_in_vals:
        #         vals = {}
        #         vals['assigned_to'] = approved_to_in_vals
        #         res = super().write(vals)
        #     return res
        
        # else:
        res = super().write(vals)

        if not self.active:
            for variant_id in self.product_variant_ids:
                variant_id.write({
                    'active': False,
                    # 'is_hidden': True,
                })

        if vals.get('state') == 'confirmed':
            for record in self:
                record.write({'active': True})
                for variant in record.product_variant_ids:
                    variant.write({
                        'active': True,
                        # 'is_hidden': True,
                    })

                # Send email to all approval users
                approval_template = self.env.ref('product_approval_email_template', raise_if_not_found=False)
                if approval_template and record.existing_user_ids:
                    email_list = [user.email_formatted for user in record.existing_user_ids if user.email]
                    if email_list:
                        approval_template.send_mail(record.id, force_send=True,
                        email_values={'email_from': self.env.user.email_formatted,
                                                'email_to': ','.join(email_list), })
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



    # @api.model
    # def create(self, vals):
    #     res = super().create(vals)
    #     if res.product_approval_id:
    #         res.product_approval_id._update_state_based_on_approvals()
    #     return res 