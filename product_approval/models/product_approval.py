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

        # print('------------------------- vals.get(assigned_to) => ', vals.get('assigned_to'))
        # print('--------------------- self.state => ', self.state)

        # if vals.get('assigned_to') or self.state == 'pending' or self.state == 'rejected':
        #     print("***************.  Return.   *******")
        #     return

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

    # @api.model
    # def _get_view(self, view_id=None, view_type='form', **options):
    #     # Clear caches to ensure the latest data is used, though often not needed here.
    #     # self.clear_caches() # Generally not recommended within _get_view as it can impact performance

    #     # Call the original _get_view method to get the base architecture and view object
    #     print("----------   in _get_view")

    #     arch, view = super()._get_view(view_id, view_type, **options)


    #     if view_type == 'form':
    #         # Get the ID of the current record being displayed, if available
    #         # This is crucial for fetching the 'is_hidden' field value.
    #         # 'res_id' is passed in options for form views.
    #         record_id = options.get('res_id')
    #         is_hidden = False # Default to not hidden

    #         if record_id:
    #             # Fetch the 'is_hidden' field value for the current record
    #             record = self.browse(record_id)
    #             if record.exists(): # Ensure the record actually exists
    #                 is_hidden = record.is_hidden # Assuming 'is_hidden' is a field on product.template

    #         _logger.info(f"Form for record ID {record_id}, is_hidden: {is_hidden}")

    #         # Iterate through all field elements in the architecture
    #         for field in arch.xpath("//field"):
    #             field_name = field.get('name')
    #             # If the 'is_hidden' field is True for the current record, make all fields read-only
    #             if is_hidden:
    #                 _logger.info(f"Setting field '{field_name}' to readonly (is_hidden is True).")
    #                 field.set('readonly', '1')
    #             else:
    #                 # If 'is_hidden' is False, ensure fields are NOT forced to readonly by this method.
    #                 # This is important if they might have 'readonly' set from other sources.
    #                 # You might want to explicitly remove 'readonly' if it's there from a previous pass.
    #                 if field.get('readonly') == '1': # Only remove if we explicitly set it previously
    #                     field.set('readonly', '0') # Or field.attrib.pop('readonly', None)

    #         # Also consider making buttons invisible or disabled if the form is read-only
    #         # This requires knowing the XPath for your specific buttons.
    #         # Example for header buttons (like 'Edit', 'Save'):
    #         # for button in arch.xpath("//header/button"):
    #         #     button_name = button.get('name')
    #         #     if is_hidden:
    #         #         button.set('invisible', '1') # Makes button invisible
    #         #         # Or set 'attrs' if you want more nuanced control (e.g., based on state)
    #         #         # button.set('attrs', "{'invisible': [('is_hidden', '=', True)]}")
    #         #     else:
    #         #         # Ensure buttons are visible if not hidden
    #         #         button.set('invisible', '0') # Or button.attrib.pop('invisible', None)

    #     return arch, view


    # @api.model
    # def _get_view(self, view_id=None, view_type='form', **options):
    #     self.clear_caches()
    #     arch, view = super()._get_view(view_id, view_type, **options)
    #     if view_type == 'form':
    #         for field in arch.xpath("//field"):

    #             print('1111111111111', field, field.get('name'))
    #             field.set('readonly', '1')
    #     return arch, view


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