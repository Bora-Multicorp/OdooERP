# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from datetime import timedelta, date


class ContactKYCApproval(models.Model):
    _name = 'res.partner.kyc.approval'
    _description = 'Vendor KYC approval'
    _rec_name = 'partner_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)
        attachment_fields = [
            'gst_certificate', 'udyam_document', 'shop_act_document',
            'shop_photos', 'shop_videos', 'pan_card_document',
            'incorporation_certificate', 'moa_aoa', 'electricity_bill'
        ]
        for record in res_list:
            for field in attachment_fields:
                attachments = record[field]
                attachments.write({
                    'res_model': self._name,
                    'res_id': record.id,
                })
        return res_list

    # @api.constrains('gst_certificate', 'udyam_document', 'shop_act_document', 'shop_photos', 'shop_videos',
    #                 'pan_card_document', 'incorporation_certificate', 'moa_aoa', 'electricity_bill')
    # def _check_attachment_limits(self):
    #     limits = {
    #         'gst_certificate': (1, 10 * 1024 * 1024),
    #         'udyam_document': (1, 10 * 1024 * 1024),
    #         'shop_act_document': (1, 10 * 1024 * 1024),
    #         'shop_photos': (10, 100 * 1024 * 1024),
    #         'shop_videos': (10, 100 * 1024 * 1024),
    #         'pan_card_document': (1, 10 * 1024 * 1024),
    #         'incorporation_certificate': (5, 10 * 1024 * 1024),
    #         'moa_aoa': (5, 10 * 1024 * 1024),
    #         'electricity_bill': (5, 10 * 1024 * 1024),
    #     }
    #     for field_name, (max_count, max_size) in limits.items():
    #         attachments = getattr(self, field_name)
    #         print('111111111', self._fields[field_name].string, len(attachments), max_count)
    #         if len(attachments) > max_count:
    #             raise ValidationError(f"Only {max_count} file(s) allowed for '{self._fields[field_name].string}'.")
    #         for attachment in attachments:
    #             if attachment.file_size and attachment.file_size > max_size:
    #                 raise ValidationError(
    #                     f"Each file in '{self._fields[field_name].string}' must be ≤ {max_size // (1024 * 1024)} MB."
    #                 )

    # @api.model
    # def _get_view(self, view_id=None, view_type='form', **options):
    #     self.clear_caches()
    #     arch, view = super()._get_view(view_id, view_type, **options)
    #     if view_type == 'form':
    #         for field in arch.xpath("//field"):
    #
    #             print('1111111111111', field, field.get('name'))
    #             field.set('readonly', '1')
    #     return arch, view

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

    @api.depends('approval_users_ids.user_id')
    def _compute_existing_users(self):
        for record in self:
            if record.approval_users_ids:
                record.existing_user_ids = [(6, 0, record.approval_users_ids.mapped('user_id').ids)]
            else:
                record.existing_user_ids = [(6, 0, [])]

    partner_id = fields.Many2one('res.partner', string="Contact")
    email = fields.Char("Email")
    point_of_contact = fields.Char("Point of Contact / Purchase Manager (Bora Multicorp)")
    poc_user = fields.Many2one('res.users', string="Point of Contact to Vendor")
    business_legal_name = fields.Char("Business Legal Name")
    is_same_trade_name = fields.Boolean(string="If Trade Name is same as Legal Name",
                                        help="Tick if trade name is same as legal name")
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
    # director_name = fields.Char(string="Name of the Owner / Director")
    # director_phone = fields.Char(string="Contact Number")
    # director_email = fields.Char(string="Email Address")
    # aadhaar_card = fields.Binary(string="Aadhaar Card")
    # aadhaar_card_filename = fields.Char()
    # pan_card = fields.Binary(string="PAN Card (Proprietor)")
    # pan_card_filename = fields.Char()
    aadhaar_pan_link = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Aadhar and PAN card linking?',
                                        required=True)
    gst_no = fields.Char(string="GST Number", required=True)
    license_registered = fields.Char(string="Any licenses registered (As per Local/State Government requirements)")
    udyam_number = fields.Char(string="Udyam Certificate Number")
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rels', 'partner_id', 'attachment_id',
                                       string="Company GST Certificate", required=False)
    shop_act_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_act_documents_rels', 'partner_id',
                                         'attachment_id',
                                         string="Shop Act documents", required=False)
    pan_card_document = fields.Many2many('ir.attachment', 'pan_card_company_documents_rels', 'partner_id',
                                         'attachment_id',
                                         string="PAN Card Document(Company)")

    udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rels', 'partner_id', 'attachment_id',
                                      string="Udyam Documents", required=False)

    gst_return_duration = fields.Selection([('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')],
                                           required=False, string="GST Return duration")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rels', 'partner_id', 'attachment_id',
                                   string="Shop Photos", required=False,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rels', 'partner_id', 'attachment_id',
                                   string="Shop Videos", required=False,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")
    ##### Partnership/PrivateCo./LLP
    no_partner_director = fields.Selection([('1', '1'),
                                            ('2', '2'),
                                            ('3', '3'),
                                            ('4', '4'),
                                            ('5', '5'),
                                            ('6', '6'),
                                            ('7', '7')], string="Number of Managing Partner / Directors")
    directors_detail = fields.One2many('director.details', 'kyc_approval_id', string="KYC Details", tracking=True)
    pan_no = fields.Char(string="PAN Number", required=False)
    comp_google_loc = fields.Char(string="Google Location of Shop", required=False)
    partner_llp_filename = fields.Char()
    partner_llp = fields.Binary(string="Partnership Deed or LLP Deed", required=False)
    moa_aoa = fields.Many2many('ir.attachment', 'vendor_kyc_moa_aoa_rels', 'partner_id', 'attachment_id',
                               string="MOA or AOA")

    cin_no = fields.Char(string="CIN number", required=False)
    electricity_bill = fields.Many2many('ir.attachment', 'vendor_kyc_electricity_bill_rels', 'partner_id',
                                        'attachment_id',
                                        string="Electricity bill", required=False)
    incorporation_certificate = fields.Many2many('ir.attachment', 'incorportaion_certificate_rels', 'partner_id',
                                                 'attachment_id',
                                                 string="Incorporation Certificate")
    #####
    ##### Bank Details
    bank_detail = fields.One2many('bank.details', 'kyc_approval_id', string="Banks Detail")
    ##### Address Details
    address_detail = fields.One2many('address.details', 'kyc_approval_id', string="Address Detail")

    deadline = fields.Date('Deadline Date', tracking=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('pending', 'Pending Approval'),
                              ('confirmed', 'Confirmed'),
                              ('rejected', 'Rejected'),
                              ('expired', 'Expired')], default='draft', required=False, string="Status", tracking=True)
    approval_users_ids = fields.One2many('approval.users', 'kyc_approval_id', 'Approval Authorities',
                                         help='Approval Authority Details')
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_users', store=True)
    is_approved = fields.Boolean(related='partner_id.is_approved', store=True)
    approval_date = fields.Datetime(string="Approval Date", tracking=True)
    is_rejected = fields.Boolean(tracking=True)
    rejection_date = fields.Datetime(string="Rejection Date", tracking=True)
    rejection_reason = fields.Text('Rejection Reason', tracking=True)

    def confirm_submit_form(self):
        if not self.approval_users_ids:
            raise ValidationError(_("Please Add Approval Authority before Submit Request"))
        if self.id:
            self.write({'state': 'pending'})
            self._update_assigned_to()

    def set_as_draft(self):
        if self.id:
            self.write({
                'state': 'draft',
                'rejection_date': False,
                'rejection_reason': False,
                'is_rejected': False,
            })
            self.partner_id.sudo().write({
                'rejection_date': False,
                'rejection_reason': False,
                'is_rejected': False,
                'is_kyc': True,
            })

            # Reset approval users' decision fields
            self.approval_users_ids.write({
                'state': False,
                'remark': False,
                'action_date': False,
            })

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
            # Send email to assign to user
            # assign_to_template = self.env.ref('custom_contact.assign_to_email_template',
            #                                   raise_if_not_found=False)
            # if rec.assigned_to and assign_to_template and rec.existing_user_ids:
            #     email_list = [user.email_formatted for user in rec.existing_user_ids if user.email]
            #     if email_list:
            #         assign_to_template.send_mail(rec.id, force_send=True,
            #                                      email_values={'email_from': self.env.user.email_formatted,
            #                                                    'email_to': rec.assigned_to.email_formatted,
            #                                                    'email_cc': ','.join(email_list),
            #                                                    })
            # Schedule activity to assign to user
            if rec.assigned_to:
                rec._schedule_kyc_assignment_activity()

    def _schedule_kyc_assignment_activity(self):
        for rec in self:
            rec.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=f'KYC Approval for: {rec.partner_id.name}',
                note=_("You have been assigned to review this KYC approval."),
                user_id=rec.assigned_to.id,
                date_deadline=fields.Date.context_today(rec),
            )

            rec.env['bus.bus']._sendone(rec.assigned_to.partner_id,
                'simple_notification',
                {
                    'type': 'success',
                    'title': _("KYC Approval for: %s") % rec.partner_id.name,
                    #'message': _("Activity assigned to you: %s") % rec.assigned_to.name,
                    'message': _("Activity assigned to you."),
                    'sticky': True,
                },
            )

    def _update_state_based_on_approvals(self):
        for rec in self:
            states = rec.approval_users_ids.mapped('state')
            if any(s == 'reject' for s in states):
                rec.state = 'rejected'
            elif states and all(s == 'approve' for s in states):
                rec.state = 'confirmed'

    def write(self, vals):
        res = super().write(vals)
        attachment_fields = [
            'gst_certificate', 'udyam_document', 'shop_act_document',
            'shop_photos', 'shop_videos', 'pan_card_document',
            'incorporation_certificate', 'moa_aoa', 'electricity_bill'
        ]
        for record in self:
            for field in attachment_fields:
                attachments = record[field]
                if attachments:
                    attachments.write({
                        'res_model': self._name,
                        'res_id': record.id,
                    })

        def _schedule_activity(record, user, title, note):
            record.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=title,
                note=note,
                user_id=user.id,
                date_deadline=fields.Date.context_today(record),
            )

        def _send_notification(record, user, title, message):
            record.env['bus.bus']._sendone(
                user.partner_id,
                'simple_notification',
                {
                    'type': 'warning',
                    'title': title,
                    'message': message,
                    'sticky': True,
                },
            )

        for record in self:
            if vals.get('state') == 'confirmed':
                if record.partner_id and not record.partner_id.is_approved:
                    now = fields.Datetime.now()
                    one_year = now + relativedelta(years=1)

                    # Update partner and record
                    record.partner_id.write({
                        'is_approved': True,
                        'deadline': one_year,
                    })
                    record.write({
                        'approval_date': now,
                        'deadline': one_year,
                    })

                    # Send approval email to all users
                    # approval_template = self.env.ref('custom_contact.kyc_approval_email_template', raise_if_not_found=False)
                    # if approval_template and record.existing_user_ids:
                    #     email_list = [user.email_formatted for user in record.existing_user_ids if user.email]
                    #     if email_list:
                    #         approval_template.send_mail(record.id, force_send=True, email_values={
                    #             'email_from': self.env.user.email_formatted,
                    #             'email_to': ','.join(email_list),
                    #         })

                    # Send approval activity and notification
                    for user in record.existing_user_ids:
                        _schedule_activity(
                            record, user,
                            title=f"KYC Approved for: {record.partner_id.name}",
                            note=_(
                                "KYC for %s has been approved. Please take necessary follow-up action.") % record.partner_id.name
                        )
                        _send_notification(
                            record, user,
                            title=_("KYC Approved for: %s") % record.partner_id.name,
                            message=_(
                                "KYC for %s has been approved. Please check the system for further details.") % record.partner_id.name
                        )

            elif vals.get('state') == 'rejected':
                # Send rejection email and activity
                # rejection_template = self.env.ref('custom_contact.kyc_rejection_email_template', raise_if_not_found=False)
                # if record.partner_id and record.existing_user_ids and rejection_template:
                #     email_list = [user.email_formatted for user in record.existing_user_ids if user.email]
                #     if email_list:
                #         rejection_template.send_mail(record.id, force_send=True, email_values={
                #             'email_from': self.env.user.email_formatted,
                #             'email_to': ','.join(email_list),
                #         })

                for user in record.existing_user_ids:
                    _schedule_activity(
                        record, user,
                        title=f"KYC Rejected for: {record.partner_id.name}",
                        note=_("KYC for %s has been rejected. Please take necessary action.") % record.partner_id.name
                    )
                    _send_notification(
                        record, user,
                        title=_("KYC Rejected for: %s") % record.partner_id.name,
                        message=_(
                            "KYC for %s has been rejected. Please check the system for more details.") % record.partner_id.name
                    )

        return res


class ApprovalUsers(models.Model):
    _name = "approval.users"
    _rec_name = 'kyc_approval_id'
    _description = "Approval Users"
    _order = "sequence"

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="KYC Approval")
    sequence = fields.Integer(string='Sequence')
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


### Directors Details
class DirectorDetails(models.Model):
    _name = "director.details"
    _rec_name = 'name'
    _description = "Directors Details"

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="KYC Approval")
    designation = fields.Char(string="Designation")
    name = fields.Char(string="Name")
    contact_no = fields.Char(string="Contact Number")
    email = fields.Char(string="E-mail Address")
    aadhaar_card = fields.Binary(string="Aadhaar Card")
    aadhaar_card_filename = fields.Char()
    pan_card = fields.Binary(string="PAN Card")
    pan_card_filename = fields.Char()
    aadhaar_card_attachments = fields.Many2many('ir.attachment', 'vendor_bank_aadhaar_card_rel', 'kyc_approval_id',
                                                'attachment_id', string="Aadhaar Card", required=False)
    pan_card_attachments = fields.Many2many(
        'ir.attachment',
        'vendor_bank_pan_card_rel', 'kyc_approval_id',
        'attachment_id',
        string="PAN Card",
        required=False
    )
    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)
        for record in res_list:
            for attachment in record.aadhaar_card_attachments | record.pan_card_attachments:
                attachment.write({
                    'res_model': self._name,
                    'res_id': record.id,
                })
        return res_list


##### Bank Details
class BankDetail(models.Model):
    _name = "bank.details"
    _rec_name = 'bank_name'
    _description = "Bank Details"

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="KYC Approval")
    bank_name = fields.Char(string="Bank Name", required=False)
    account_no = fields.Char(string="Account Number", required=False)
    ifsc_code = fields.Char(string="IFSC Code", required=False)
    bank_address = fields.Char(string="Bank Address", required=False)
    bank_cheque_attachments = fields.Many2many('ir.attachment', 'vendor_bank_detail_cheque_rel', 'kyc_approval_id',
                                               'attachment_id', string="Cancelled Cheques", required=False)

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)
        for record in res_list:
            for attachment in record.bank_cheque_attachments:
                attachment.write({
                    'res_model': self._name,
                    'res_id': record.id,
                })
        return res_list


##### Principal Place of Business
class AddressDetail(models.Model):
    _name = "address.details"
    _description = "Address Details"
    _rec_name = 'kyc_approval_id'

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="KYC Approval")
    business_street = fields.Char("Address", required=False)
    business_city = fields.Char("City", required=False)
    business_pincode = fields.Char("Pincode", required=False)
    business_phone = fields.Char("Contact Number", required=False)
    business_email = fields.Char("Email Address")
    business_state_id = fields.Many2one('res.country.state', string='Business State',
                                        domain="[('country_id', '=?', business_country_id)]")
    business_country_id = fields.Many2one('res.country', string='Business Country')
