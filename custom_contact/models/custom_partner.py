# -*- coding: utf-8 -*-
from email.policy import default

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re
from datetime import timedelta, date

class CustomContact(models.Model):
    _inherit = 'res.partner'

    _sql_constraints = [
        # SQL-level constraint (optional if email is NULLable)
        ('unique_email', 'UNIQUE(email)', 'Email address must be unique.')
    ]

    @api.constrains('city', 'zip')
    def _check_city_zip_format(self):
        for rec in self:
            # Validate City: only letters and spaces
            if rec.city and not re.fullmatch(r"[A-Za-z\s]+", rec.city):
                raise ValidationError(
                    _("City must contain only letters and spaces.\nInvalid Value: %s") % rec.city)

            # Validate Zip (Pincode): exactly 6 digits
            if rec.zip and not re.fullmatch(r"\d{6}", rec.zip):
                raise ValidationError(
                    _("Pincode must be exactly 6 digits (e.g., 400001).\nInvalid Value: %s") % rec.zip)

    @api.constrains('email')
    def _check_duplicate_email(self):
        email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')  # Basic email format
        for rec in self:
            if rec.email:
                # Check valid email format
                if not email_pattern.match(rec.email):
                    raise ValidationError(_(
                        "Email must be valid (e.g., user@example.com). %s"
                    ) % rec.email)

                # Check duplicate email
                existing = self.env['res.partner'].search([
                    ('email', '=', rec.email),
                    ('id', '!=', rec.id)
                ], limit=1)
                if existing:
                    raise ValidationError(
                        _("The email address '%s' is already used by another contact.") % rec.email
                    )

    @api.constrains('l10n_in_pan')
    def _check_pan_card_no_format(self):
        pan_pattern = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
        for rec in self:
            if rec.l10n_in_pan and not pan_pattern.match(rec.l10n_in_pan.upper()):
                raise ValidationError(
                    _("PAN Number must be in the format: 5 letters, 4 digits, and 1 letter (e.g., ABCDE1234F).")
                )

    # @api.onchange('phone', 'mobile', 'country_id')
    # def _onchange_validate_phone_numbers(self):
    #     for rec in self:
    #         country = rec.country_id
    #         phone_code = country.phone_code or ''
    #         country_name = country.name or 'the selected country'
    #
    #         def validate_number(value, label):
    #             if not value:
    #                 return None
    #
    #             clean_number = re.sub(r'[\s\-()]', '', value)
    #             if not re.fullmatch(r'\+?\d{7,15}', clean_number):
    #                 return f"{label} must be a valid phone number with 7–15 digits (e.g., +{phone_code}XXXXXXXXXX) for {country_name}.\nInvalid Value: {value}"
    #             if phone_code and not clean_number.startswith(f"+{phone_code}") and not clean_number.startswith(
    #                     phone_code):
    #                 return f"{label} should start with the country code +{phone_code} (for {country_name}).\nInvalid Value: {value}"
    #
    #         phone_warning = validate_number(rec.phone, "Phone")
    #         mobile_warning = validate_number(rec.mobile, "Mobile")
    #
    #         if phone_warning or mobile_warning:
    #             return {
    #                 'warning': {
    #                     'title': "Phone Number Format Warning",
    #                     'message': f"{phone_warning or ''}\n{mobile_warning or ''}".strip()
    #                 }
    #             }

    @api.constrains('vat')
    def _check_gst_no_format(self):
        gst_pattern = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
        for rec in self:
            if rec.vat and not gst_pattern.match(rec.vat.upper()):
                raise ValidationError(_(
                    "Invalid GST Number: '%s'. It must follow the 15-character format (e.g., 27ABCDE1234F1Z5)."
                ) % rec.vat)

    @api.constrains('phone', 'mobile')
    def _check_phone_mobile_number(self):
        phone_pattern = re.compile(r'^\d{10}$')  # Exactly 10 digits
        mobile_pattern = re.compile(r'^(\d{10}|\d{12})$')  # Exactly 10 OR 12 digits

        for rec in self:
            if rec.phone and not phone_pattern.fullmatch(rec.phone):
                raise ValidationError(_(
                    "Phone number must be exactly 10 digits.\nInvalid Value: %s"
                ) % rec.phone)

            if rec.mobile and not mobile_pattern.fullmatch(rec.mobile):
                raise ValidationError(_(
                    "Mobile number must be either 10 or 12 digits.\nInvalid Value: %s"
                ) % rec.mobile)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)

        action_id = options.get('action_id')
        contact_action = self.env.ref('contacts.action_contacts', raise_if_not_found=False)

        if action_id and contact_action and action_id != contact_action.id:
            if view_type in ('kanban', 'list', 'form'):
                for node in arch.xpath('//form | //kanban | //list'):
                    node.set('create', 'false')
        return arch, view

    custom_type = fields.Many2one('res.partner.location.type', string="Type", tracking=True,
                                  help='Contact Location Type', copy=False)
    custom_address_type = fields.Many2one('res.partner.address.type', string="Address Type", tracking=True,
                                          help='Contact Address Type', copy=False)
    tally_name = fields.Char(string="Tally Name", tracking=True)
    purpose = fields.Char(string="Purpose", tracking=True)
    # Customer/Vendor KYC Details
    is_vendor = fields.Boolean(string="Is Vendor?", tracking=True)
    is_customer = fields.Boolean(string="Is Customer?", tracking=True)
    is_kyc = fields.Boolean(string="Is KYC?", tracking=True)
    is_approved = fields.Boolean(string="Is Approved?", tracking=True)
    approval_date = fields.Datetime(string="Approval Date", tracking=True)
    is_rejected = fields.Boolean(string="Is Rejected?", tracking=True)
    rejection_date = fields.Datetime(string="Rejection Date", tracking=True)
    rejection_reason = fields.Text('Rejection Reason', tracking=True)
    deadline = fields.Date('KYC Deadline', tracking=True)

    kyc_details = fields.One2many('res.partner.kyc.approval', 'partner_id', string="KYC Details", tracking=True)

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_approved') is True:
            for record in self:
                if record.is_vendor:
                    record.supplier_rank = (record.supplier_rank or 0) + 1
                if record.is_customer:
                    record.customer_rank = (record.customer_rank or 0) + 1
        return res

    survey_ids = fields.One2many('survey.user_input', 'partner_id', string='Surveys')
    survey_count = fields.Integer(string="Survey Count",
                                  groups='sales_team.group_sale_salesman',
                                  compute='_compute_survey_count')

    def _compute_survey_count(self):
        for partner in self:
            if not self.env.user._has_group('sales_team.group_sale_salesman'):
                partner.survey_count = 0
                continue

            # Get self and child partners
            all_partners = self.with_context(active_test=False).search([('id', 'child_of', partner.id)])
            partner_ids = all_partners.ids
            partner_emails = [p.email for p in all_partners if p.email]

            # Search for surveys by partner_id or email
            domain = ['|',
                      ('partner_id', 'in', partner_ids),
                      ('email', 'in', partner_emails)]

            survey_count = self.env['survey.user_input'].with_context(active_test=False).search_count(domain)
            partner.survey_count = survey_count

    def action_view_survey_response(self):
        '''
        This function returns an action that displays the survey response from partner.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_user_input')
        action['domain'] = ['|', ('partner_id', '=', self.id), ('email', '=', self.email)]
        return action

    def trigger_email_kyc_expiry_follow_up(self):
        today = fields.Date.today()
        template = self.env.ref('custom_contact.kyc_expiry_reminder_template', raise_if_not_found=False)

        # Get email_formatted list from approval config
        approval_users = self.env['vendor.approval.config'].search([])
        email_list = [user.user_id.email_formatted for user in approval_users if user.user_id and user.user_id.email]
        email_to = ','.join(email_list) if email_list else False

        # Day 0: KYC Expired
        expired_partners = self.search([('deadline', '=', today)])
        for partner in expired_partners:
            if template and email_to:
                template.with_context(mail_body_type='expired').send_mail(
                    partner.id,
                    force_send=True,
                    email_values={'email_to': email_to}
                )

            update_vals = {
                'deadline': False,
                'is_kyc': False,
                'is_approved': False,
            }
            if partner.is_vendor:
                update_vals['supplier_rank'] = 0
            if partner.is_customer:
                update_vals['customer_rank'] = 0

            partner.write(update_vals)

            # Log note in chatter
            partner.message_post(
                body="KYC Expired: Deadline reached. Status reset.",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

        # Day 1–3: KYC Reminders
        for days_left in [1, 2, 3]:
            target_date = today + timedelta(days=days_left)
            partners = self.search([('deadline', '=', target_date)])
            for partner in partners:
                if template and email_to:
                    template.with_context(
                        mail_body_type='reminder',
                        days_left=days_left
                    ).send_mail(
                        partner.id,
                        force_send=True,
                        email_values={'email_to': email_to}
                    )


