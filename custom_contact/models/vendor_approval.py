# -*- coding: utf-8 -*-

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta

class ContactKYCApproval(models.Model):
    _name = 'res.partner.kyc.approval'
    _description = 'Contact KYC approvals'
    _rec_name = 'partner_id'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        vendor_approval_users = self.env['vendor.approval.config'].sudo().search([])

        if vendor_approval_users:
            approval_user_vals = []
            for approval in vendor_approval_users:
                approval_user_vals.append((0, 0, {
                    'sequence': approval.sequence,
                    'user_id': approval.user_id.id,
                    # 'job_id': user.employee_id.job_title or '',  # fallback to empty if not set
                }))
            defaults['approval_users_ids'] = approval_user_vals
        return defaults

    partner_id = fields.Many2one('res.partner', string="Contact")
    email = fields.Char("Email")
    point_of_contact = fields.Char("Point of Contact / Purchase Manager (Bora Multicorp)")
    business_legal_name = fields.Char("Business Legal Name")
    business_trade_name = fields.Char("Business Trade Name")
    business_street = fields.Char("Address")
    business_city = fields.Char("City")
    business_pincode = fields.Char("Pincode")
    additional_street = fields.Char("Address")
    additional_city = fields.Char("City")
    additional_zip = fields.Char("Pincode")
    additional_phone = fields.Char("Contact Number")
    additional_email = fields.Char("Email Address")
    const_business = fields.Selection([('Sole Proprietor', 'Sole Proprietor'),
                                       ('Partnership', 'Partnership'),
                                       ('Pvt Ltd Co.', 'Pvt Ltd Co.'),
                                       ('LLP', 'LLP'),
                                       ('HUF(Karta)', 'HUF(Karta)'),
                                       ('Other', 'Other'),
                                       ], string="Constitution of Business", required=False)
    # const_business = fields.Many2one('constitution.business', string="Constitution of Business", required=True)
    other_business = fields.Char("If Other, Specify?")
    # no_partner_director = fields.Many2one('number.partner.director', string="Number of Managing Partner / Directors")
    director_name = fields.Char(string="Name of the Owner / Director")
    director_phone = fields.Char(string="Contact Number")
    director_email = fields.Char(string="Email Address")
    aadhaar_card = fields.Binary(string="Aadhaar Card")
    pan_card = fields.Binary(string="PAN Card (Proprietor)")
    gst_no = fields.Char(string="GST Number")
    udyam_number = fields.Char(string="Udyam Certificate Number")
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rel1', 'wizard_id', 'attachment_id',
                                       string="Company GST Certificate", required=False)

    udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rel1', 'wizard_id', 'attachment_id',
                                      string="Shop Act documents / Udyam Documents", required=True)

    gst_return_duration = fields.Selection([('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')],
                                           required=False, string="GST Return duration")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rel1', 'wizard_id', 'attachment_id',
                                   string="Shop Photos", required=False,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rel1', 'wizard_id', 'attachment_id',
                                   string="Shop Videos", required=False,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    bank_name = fields.Char(string="Bank Name", required=False)
    account_no = fields.Char(string="Account Number", required=False)
    ifsc_code = fields.Char(string="IFSC Code", required=False)
    bank_address = fields.Char(string="Bank Address", required=False)
    bank_cheque_attachments = fields.Many2many('ir.attachment', 'vendor_kyc_bank_cheque_rel1', 'wizard_id',
                                               'attachment_id', string="Cancelled Cheques")

    deadline = fields.Date('Deadline Date')
    state = fields.Selection([('draft', 'Draft'),
                              ('pending', 'Pending Approval'),
                              ('confirmed', 'Confirmed'),
                              ('rejected', 'Rejected'),
                              ('expired', 'Expired')], default='draft', required=False, string="Status")
    approval_users_ids = fields.One2many('approval.users', 'kyc_approval_id', 'Approval Authorities',
                                         help='Approval Authority Details')
    assigned_to = fields.Many2one('res.users', string='Assigned To')
    existing_user_ids = fields.Many2many('res.users', compute='_compute_approval_user_ids', store=False)
    is_approved = fields.Boolean(related='partner_id.is_approved', store=True)

    @api.depends('existing_user_ids.user_id')
    def _compute_approval_user_ids(self):
        for record in self:
            # Get the user_ids from related approval_detail_ids
            user_ids = record.existing_user_ids.mapped('user_id')
            # Assign the collected users to approval_user_ids
            record.existing_user_ids = [(6, 0, user_ids.ids)]

    def confirm_submit_form(self):
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

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'confirmed':
            for record in self:
                if record.partner_id and not record.partner_id.is_approved:
                    record.partner_id.write({'is_approved': True, 'deadline': fields.Datetime.now() + relativedelta(years=1)})
                    # Set deadline to 1 year from now
                    record.write({'deadline': fields.Datetime.now() + relativedelta(years=1)})
        return res

class ApprovalUsers(models.Model):
    _name = "approval.users"
    _rec_name = 'kyc_approval_id'
    _description = "Approval Users"
    _order = "sequence"

    sequence = fields.Integer(string='Sequence')
    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="KYC Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected')], string="Action")
    remark = fields.Text('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.kyc_approval_id:
                rec.kyc_approval_id._update_state_based_on_approvals()
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.kyc_approval_id:
            res.kyc_approval_id._update_state_based_on_approvals()
        return res
