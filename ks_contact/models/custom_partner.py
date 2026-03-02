# -*- coding: utf-8 -*-
import re
from datetime import timedelta, date
from lxml import etree
from odoo.exceptions import ValidationError

from odoo import api, fields, models, _


class CustomContact(models.Model):
    _inherit = 'res.partner'

    _sql_constraints = [
        # SQL-level constraint (optional if email is NULLable)
        ('unique_email', 'UNIQUE(email)', 'Email address must be unique.')
    ]

    is_expired = fields.Boolean(compute='_compute_is_expired')

    @api.depends('deadline')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            # Check if deadline is in the past
            rec.is_expired = rec.deadline and rec.deadline <= today

    @api.constrains('city', 'zip')
    def _check_city_zip_format(self):
        """
        Validate city and zip/pincode formatting.

        City:
            - Must contain only letters, spaces, or hyphens.
            - Regex: ^[A-Za-z\s\-]+$

        Zip (Pincode):
            - Must be exactly 6 digits.
            - Regex: ^\d{6}$

        Raises
        ------
        ValidationError:
            If city or pincode does not match the required format.
        """
        city_regex = re.compile(r"^[A-Za-z\s\-]+$")
        zip_regex = re.compile(r"^\d{6}$")

        for rec in self:
            # Validate City
            if rec.city and not city_regex.match(rec.city):
                raise ValidationError(
                    _("City must contain only letters, spaces, or hyphens.\nInvalid Value: %s") % rec.city
                )

            # Validate Pincode (6 digits)
            if rec.zip and not zip_regex.match(rec.zip):
                raise ValidationError(
                    _("Pincode must be exactly 6 digits (e.g., 400001).\nInvalid Value: %s") % rec.zip
                )

    @api.constrains('email')
    def _check_duplicate_email(self):
        """
        Validate email format and ensure uniqueness.

        Email:
            - Must follow a basic valid pattern.
            - Regex: ^[\w\.-]+@[\w\.-]+\.\w+$
            - Must be unique across all partners (case-insensitive).

        Raises
        ------
        ValidationError:
            If email format is invalid or the email is already assigned
            to another partner.
        """
        email_regex = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')

        for rec in self:
            email = rec.email

            # Skip if no email set
            if not email:
                continue

            # Validate email format
            if not email_regex.match(email):
                raise ValidationError(
                    _("Invalid email format: %s. Expected format: user@example.com.") % email
                )

            # Check duplicate email (case insensitive)
            existing = self.env['res.partner'].search([
                ('email', '=ilike', email),
                ('id', '!=', rec.id)
            ], limit=1)

            if existing:
                raise ValidationError(
                    _("The email address '%s' is already used by another contact.") % email
                )

    @api.constrains('l10n_in_pan')
    def _check_pan_card_no_format(self):
        """
        Validate Indian PAN number format and enforce uniqueness.

        PAN Format:
            - 5 uppercase letters
            - 4 digits
            - 1 uppercase letter
            Example: ABCDE1234F

        Raises
        ------
        ValidationError:
            If PAN format is invalid or duplicate PAN is found.
        """
        pan_regex = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')

        for rec in self:
            pan = (rec.l10n_in_pan or "").upper()

            # Skip empty PAN
            if not pan:
                continue

            # Validate PAN format
            if not pan_regex.match(pan):
                raise ValidationError(
                    _("Invalid PAN format: %s. Expected format: ABCDE1234F.") % rec.l10n_in_pan
                )

            # Validate uniqueness (case-insensitive)
            duplicate = self.search([
                ('l10n_in_pan', '=ilike', pan),
                ('id', '!=', rec.id)
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    _("PAN number '%s' is already assigned to another contact.") % rec.l10n_in_pan
                )

    # @api.constrains('is_customer', 'is_vendor')
    # def _check_customer_vendor_exclusive(self):
    #     for rec in self:
    #         if rec.is_customer and rec.is_vendor:
    #             raise ValidationError(
    #                 "A partner cannot be both a Customer and a Vendor. Please uncheck one."
    #             )

    @api.constrains('is_vendor', 'vendor_type')
    def _check_vendor_type_required(self):
        """Vendor Type is required when Is Vendor is checked."""
        for rec in self:
            if rec.is_vendor and not rec.vendor_type:
                raise ValidationError(
                    _("Vendor Type is required when the contact is marked as a Vendor. Please select Type 1 or Type 2.")
                )

    @api.constrains('vat')
    def _check_gst_no_format(self):
        gst_pattern = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
        for rec in self:
            if rec.vat and not gst_pattern.match(rec.vat.upper()):
                raise ValidationError(_(
                    "Invalid GST Number: '%s'. It must follow the 15-character format (e.g., 27ABCDE1234F1Z5)."
                ) % rec.vat)

    @api.constrains('mobile', 'country_id')
    def _check_mobile_number_format(self):
        for rec in self:
            if not rec.mobile:
                continue

            # 1) Strip non-digits
            cleaned_number = re.sub(r'\D', '', rec.mobile)

            # 2) Remove leading country code (as string!)
            if rec.country_id and rec.country_id.phone_code:
                code = str(rec.country_id.phone_code)
                if code and cleaned_number.startswith(code):
                    cleaned_number = cleaned_number[len(code):]

            # 3) Validate exactly 10 digits
            if not re.fullmatch(r'\d{10}', cleaned_number):
                raise ValidationError(
                    "Mobile number must be exactly 10 digits after removing the country code."
                )

    @api.constrains('phone', 'country_id')
    def _check_phone_number_format(self):
        for rec in self:
            if not rec.phone:
                continue

            # 1) Remove all non-digits
            cleaned_number = re.sub(r'\D', '', rec.phone)

            # 2) Remove country code if present
            if rec.country_id and rec.country_id.phone_code:
                code = str(rec.country_id.phone_code)
                if code and cleaned_number.startswith(code):
                    cleaned_number = cleaned_number[len(code):]

            # 3) Validate exactly 10 digits
            if not re.fullmatch(r'\d{10}', cleaned_number):
                raise ValidationError(
                    _("Phone number must be exactly 10 digits after removing the country code.")
                )

    @api.onchange('country_id')
    def _onchange_country_mobile(self):
        if self.country_id:
            # Get the country calling code and ensure it starts with '+'
            calling_code = str(self.country_id.phone_code) if self.country_id.phone_code else ''
            if calling_code and not calling_code.startswith('+'):
                calling_code = '+' + calling_code

            if self.mobile:
                # Remove any existing country code at the start (e.g., +91 or +1)
                # Then remove all spaces
                self.mobile = re.sub(r'^\+\d+', '', self.mobile).replace(' ', '').strip()


    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id, view_type, **options)
        if 'action_id' in options:
            vendor_action = self.env.ref('account.res_partner_action_supplier', raise_if_not_found=False)

            # ✅ Only disable "New" button on Vendor action
            if vendor_action and vendor_action.id == options['action_id']:
                root = etree.fromstring(result['arch'])
                root.set('create', 'false')  # removes "New" button
                result['arch'] = etree.tostring(root)

        return result

    custom_type = fields.Many2one('res.partner.location.type', string="Type", tracking=True,
                                  help='Contact Location Type', copy=False)
    custom_address_type = fields.Many2one('res.partner.address.type', string="Address Type", tracking=True,
                                          help='Contact Address Type', copy=False)
    tally_name = fields.Char(string="Tally Name", tracking=True)
    purpose = fields.Char(string="Purpose", tracking=True)
    # Customer/Vendor KYC Details
    is_vendor = fields.Boolean(string="Is Vendor?", tracking=True)
    vendor_type = fields.Selection(
        [('1', 'Type 1'), ('2', 'Type 2')],
        string='Vendor Type',
        tracking=True,
        copy=False,
        help='Required for vendors. Type 2 vendors bypass the KYC process and are auto-approved.',
    )
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
        # Detect Type 2 → Type 1 switch before write (for KYC reset)
        type2_to_type1 = {}
        if 'vendor_type' in vals and vals.get('vendor_type') == '1':
            for record in self:
                if record.vendor_type == '2':
                    type2_to_type1[record.id] = True

        res = super().write(vals)

        for record in self:
            # If marked as Customer → directly set customer_rank (no approval needed)
            if vals.get('is_customer') or record.is_customer:
                if record.customer_rank != 1:
                    super(CustomContact, record.sudo()).write({'customer_rank': 1})

            # If marked as Vendor → require approval (or auto-approve for Type 2)
            if vals.get('is_approved') is True and (vals.get('is_vendor') or record.is_vendor):
                if record.supplier_rank != 1:
                    super(CustomContact, record.sudo()).write({'supplier_rank': 1})

            # KYC bypass for Type 2 vendors: auto-set is_kyc and is_approved so no KYC form is needed
            if record.is_vendor and record.vendor_type == '2':
                partner_vals = {'is_kyc': True, 'is_approved': True}
                if record.supplier_rank != 1:
                    partner_vals['supplier_rank'] = 1
                if not record.is_kyc or not record.is_approved:
                    super(CustomContact, record.sudo()).write(partner_vals)
            # When switching from Type 2 to Type 1: clear KYC so they must complete the process (if no real KYC record)
            elif type2_to_type1.get(record.id):
                kyc_confirmed = record.kyc_details.filtered(lambda k: k.state == 'confirmed')
                if not kyc_confirmed and (record.is_kyc or record.is_approved):
                    super(CustomContact, record.sudo()).write({
                        'is_kyc': False,
                        'is_approved': False,
                    })

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

    @api.model
    def trigger_schedule_activity_kyc_expiry_follow_up(self):
        today = fields.Date.context_today(self)

        activity_type = self.env.ref('mail.mail_activity_data_todo')
        partner_model = self.env['res.partner']
        activity_model = self.env['mail.activity']
        partner_model_id = self.env.ref('base.model_res_partner').id

        # 1️⃣ Find partners whose latest KYC expires today
        partners = partner_model.search([
            ('deadline', '=', today)
        ])

        for partner in partners:
            # 2️⃣ Prevent duplicate activity
            existing_activity = activity_model.search([
                ('res_model_id', '=', partner_model_id),
                ('res_id', '=', partner.id),
                ('summary', '=', 'KYC Expiry Follow-up'),
            ], limit=1)

            if not existing_activity:
                activity_model.create({
                    'activity_type_id': activity_type.id,
                    'summary': 'KYC Expiry Follow-up',
                    'note': f'KYC for {partner.name} expires today. Please re-verify.',
                    'date_deadline': today,
                    'user_id': partner.user_id.id or self.env.user.id,
                    'res_model_id': partner_model_id,
                    'res_id': partner.id,
                })
