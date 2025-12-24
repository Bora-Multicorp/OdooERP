import logging
from lxml import etree
from odoo.exceptions import UserError, ValidationError

from odoo import api, fields, models, _

# -*- coding: utf-8 -*-

_logger = logging.getLogger(__name__)


class ProductApproval(models.Model):
    _inherit = 'product.template'
    _description = 'Product Approval Queue'

    is_hidden_for_approval = fields.Boolean(default=False)

    is_approved = fields.Boolean(string='Is Approved', default=False,
                                 help="Indicates if the product has been approved.")

    product_id = fields.Char(store=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected')
    ], default='draft', string='Status', tracking=True)

    approval_users_ids = fields.One2many('product.approval.users', 'ks_product_approval_id', 'Approval Authorities',
                                         help='Approval Authority Details')
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_users', store=True)

    def bulk_submit_for_approval(self):

        if not self.approval_users_ids:
            raise ValidationError("Please Add Approval Authority before Submit Request.")

        number_of_product_for_approvals = 0
        for product in self:
            if product.id:
                if product.state == 'draft':
                    product.write({'state': 'pending'})
                    product._update_assigned_to(False)
                    number_of_product_for_approvals += 1

        if self:  # Always check if the recordset is not empty before accessing by index
            first_product = self[0]
            title = f"Total {number_of_product_for_approvals} new products are assigned to you for the approval."
            message = "Activities are assigned to you."
            partner_id = first_product.assigned_to.partner_id
            type = "success"
            if number_of_product_for_approvals == 1:
                title = f"Product approval request for {first_product.name} assigned."
                message = "Activity assigned to you."
            elif number_of_product_for_approvals == 0:
                title = f"No products in 'Draft' state were found among your selection. Please select products that are in the 'Draft' state to proceed."
                message = ""
                type = "danger"
                partner_id = self.env.user.partner_id

            first_product.env['bus.bus']._sendone(
                partner_id,
                'simple_notification',
                {
                    'type': type,
                    'title': title,
                    'message': message,
                    'sticky': True,
                },
            )

            if partner_id != self.env.user.partner_id:
                title = "Product successfully submitted for approval."
                if number_of_product_for_approvals > 1:
                    title = f"Total {number_of_product_for_approvals} products are successfully submitted for approval."
                if number_of_product_for_approvals > 0:
                    title = f"Product successfully submitted for approval."

                first_product.env['bus.bus']._sendone(
                    self.env.user.partner_id,
                    'simple_notification',
                    {
                        'type': "info",
                        'title': title,
                        'message': "",
                        'sticky': True,
                    },
                )

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

    def assign_users(self, approvers):
        approval_user_vals = []
        for index, approval in enumerate(approvers):
            approval_user_vals.append((0, 0, {
                'sequence': index + 1,
                'user_id': approval.user_id.id,
            }))
        self.write({
            'approval_users_ids': approval_user_vals,
            'state': 'pending'
        })

        if self.id:
            self._update_assigned_to()

    def set_set_draft(self):
        self.write({
            'state': 'draft'
        })

    def confirm_submit_form(self):
        approval_users = self.env['product.approval.config'].sudo().search([])
        if not approval_users:
            raise ValidationError("Please add confirmation approval authority before submit request.")

        view_id = self.env.ref(
            "ks_product_approval.view_ks_product_approval_user_picker_wizard"
        )

        return {'type': 'ir.actions.act_window',
                'name': _('Product Approval Picker'),
                'res_model': 'product.approval.user.picker.wizard',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': view_id.id,
                'context': {'default_product_id': self.id,'default_company_id': self.env.company.id},
                }

    def approve_by_manager(self):
        self.write({'state': 'confirmed'})

    def _update_assigned_to(self, send_notification=True):
        for rec in self:
            next_user = None
            for line in sorted(rec.approval_users_ids, key=lambda x: x.sequence):
                if not line.state:
                    next_user = line.user_id
                    break
            rec.assigned_to = next_user

            if rec.assigned_to:
                rec._create_activity_and_send_notification(send_notification)

    def _update_state_based_on_approvals(self):

        for rec in self:

            # 1. check if app have approved the product
            do_all_approved = True
            is_any_approval_pending = False
            for user in self.get_last_approval_group():
                if user.state == False:
                    is_any_approval_pending = True
                    break
                if user.state != 'approve':
                    do_all_approved = False

            # 2. If approved then change state accordingly
            if is_any_approval_pending == False:
                if do_all_approved:
                    rec.state = 'confirmed'
                else:
                    rec.state = 'rejected'

    domain_field = fields.Char(compute='_compute_domain')

    @api.depends('state')
    def _compute_domain(self):
        for rec in self:
            if rec.state == 'draft':
                rec.domain_field = "[('active', '=', False), ('is_hidden_for_approval', '=', True), '|', ('create_uid', '=', uid)]"
            else:
                rec.domain_field = "[('active', '=', False), ('is_hidden_for_approval', '=', True)]"

    def action_suspend(self):
        return self.env.ref(
            "ks_product_approval.suspend_ks_product_approval_wizard_action"
        ).sudo().read()[0]

    def suspend_approval_process(self, remark):
        for product in self:
            product.message_post(
                body=f"Approval suspended by {self.env.user.display_name}. Reason: {remark}",
                message_type="comment",
                subtype_xmlid="mail.mt_note"
            )

            pending_approvers = product.approval_users_ids.filtered(lambda u: not u.state)

            pending_approvers.write({
                'state': 'suspended',
                'remark': f"By {self.env.user.name} - " + (f" {remark}" if remark else ""),
                'action_date': fields.Datetime.now()})

            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'product.template'),
                ('res_id', '=', self.ids),
                ('user_id', 'in', pending_approvers.mapped('user_id').ids),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ])

            product.write({'assigned_to': None, 'state': 'draft'})

            # send notification to creator
            product.env['bus.bus']._sendone(
                product.create_uid.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': f'Product {product.name} suspended by {self.env.user.name}. you need to initiate the approval process again.',
                    'message': '',
                    'sticky': True,
                },
            )

            # 4. in the last send info message to self
            product.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': f'Approval process suspended successfully.',
                    'message': '',
                    'sticky': True,
                },
            )

            activities.unlink()

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

    def _create_activity_and_send_notification(self, send_notification=True):
        # Schedule activity to assign to user
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'Product approval for: {rec.name}',
                note=_("You have been assigned to review this product approval."),
                user_id=rec.assigned_to.id,
                date_deadline=fields.Date.context_today(self),
            )

            if send_notification == True:
                rec.env['bus.bus']._sendone(
                    rec.assigned_to.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': _("Product approval for %s") % rec.name,
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
                            'title': f"Product '{rec.name}' successfully submitted for approval",
                            'message': "",
                            'sticky': True,
                        },
                    )

    def write(self, vals):
        res = super().write(vals)

        for record in self:
            if vals.get('state') == 'confirmed':

                for record in self:
                    record.write({'active': True})
                    for variant in record.product_variant_ids:
                        variant.write({
                            'active': True,
                            # 'is_hidden_for_approval': True,
                        })

        for rec in self:
            if not rec.active:
                for variant_id in rec.product_variant_ids:
                    variant_id.write({
                        'active': False,
                        # 'is_hidden_for_approval': True,
                    })

        return res

    def get_last_approval_group(self):
        self.ensure_one()  # This method should be called on a single record

        # Sort the approval users by sequence in ascending order
        sorted_approvals = self.approval_users_ids.sorted('sequence')

        if not sorted_approvals:
            return self.env['product.approval.users']  # Return an empty recordset

        # Get the highest sequence number
        last_sequence_number = sorted_approvals[-1].sequence

        last_group_ids = []

        # Iterate backwards from the last record
        for approval_line in reversed(sorted_approvals):
            # If the sequence number is the one we're looking for
            if approval_line.sequence == last_sequence_number:
                last_group_ids.append(approval_line.id)
                # Decrement the target sequence number for the next iteration
                last_sequence_number -= 1
            else:
                # We've found a break in the sequence, so the group is complete
                break

        # Return the records that belong to the last group, in the correct order
        return self.env['product.approval.users'].browse(reversed(last_group_ids))


class ProductApprovalUsers(models.Model):
    _name = "product.approval.users"
    _rec_name = 'ks_product_approval_id'
    _description = "Approval Users"

    sequence = fields.Integer(string='Sequence')
    ks_product_approval_id = fields.Many2one('product.template', string="Product Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected'), ('suspended', 'Suspended')],
                             string="Action")
    remark = fields.Char('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.ks_product_approval_id:
                rec.ks_product_approval_id._update_state_based_on_approvals()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super(ProductApprovalUsers, self).create(vals_list)
        for res in res_list:
            if res.ks_product_approval_id:
                res.ks_product_approval_id._update_state_based_on_approvals()
        return res_list
