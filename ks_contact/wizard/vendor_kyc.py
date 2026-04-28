# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re
import base64


class VendorKycWizard(models.TransientModel):
    _name = 'vendor.kyc.wizard'
    _description = 'Vendor KYC Wizard'

    @api.constrains('gst_certificate', 'udyam_document', 'shop_act_document', 'shop_photos', 'shop_videos',
                    'pan_card_document', 'incorporation_certificate', 'moa_aoa', 'electricity_bill')
    def _check_attachment_limits(self):
        # Fields that allow unlimited count (only size check)
        unlimited_count_fields = {
            'pan_card_document': 10 * 1024 * 1024,
            'gst_certificate': 10 * 1024 * 1024,
            'udyam_document': 10 * 1024 * 1024,
            'shop_act_document': 10 * 1024 * 1024,
            'shop_photos': 100 * 1024 * 1024,
            'shop_videos': 100 * 1024 * 1024,
            'electricity_bill': 10 * 1024 * 1024,
        }
        # Fields that still have count limits
        limited_count_fields = {
            'incorporation_certificate': (5, 10 * 1024 * 1024),
            'moa_aoa': (5, 10 * 1024 * 1024),
        }

        # Check unlimited count fields (size only)
        for field_name, max_size in unlimited_count_fields.items():
            attachments = getattr(self, field_name)
            for attachment in attachments:
                if attachment.file_size and attachment.file_size > max_size:
                    raise ValidationError(
                        f"Each file in '{self._fields[field_name].string}' must be ≤ {max_size // (1024 * 1024)} MB."
                    )

        # Check limited count fields (count and size)
        for field_name, (max_count, max_size) in limited_count_fields.items():
            attachments = getattr(self, field_name)
            if len(attachments) > max_count:
                raise ValidationError(f"Only {max_count} file(s) allowed for '{self._fields[field_name].string}'.")
            for attachment in attachments:
                if attachment.file_size and attachment.file_size > max_size:
                    raise ValidationError(
                        f"Each file in '{self._fields[field_name].string}' must be ≤ {max_size // (1024 * 1024)} MB."
                    )

    @api.constrains('partner_llp')
    def _check_partner_llp_size(self):
        max_size = 10 * 1024 * 1024  # 10 MB

        for rec in self:
            if rec.partner_llp:
                try:
                    decoded_size = len(base64.b64decode(rec.partner_llp))
                    if decoded_size > max_size:
                        raise ValidationError(_("Partner LLP document exceeds the maximum size of 10 MB."))
                except Exception:
                    raise ValidationError(_("Invalid Partner LLP file format."))

    # @api.constrains('directors_detail')
    # def _check_duplicate_directors_detail_emails(self):
    #     for wizard in self:
    #         emails = []
    #         for line in wizard.directors_detail:
    #             if line.email:
    #                 lower_email = line.email.lower()
    #                 if lower_email in emails:
    #                     raise ValidationError(
    #                         _("Duplicate email address found in Directors Details: %s") % line.email
    #                     )
    #                 emails.append(lower_email)

    @api.constrains('directors_detail', 'address_detail')
    def _check_phone_numbers(self):
        phone_pattern = re.compile(r'^[0-9]{10}$')  # Validates 10-digit numbers

        for rec in self:
            # Direct field: Director Phone
            # if rec.director_phone and not phone_pattern.fullmatch(rec.director_phone):
            #     raise ValidationError(_(
            #         "Invalid Director Contact Number:\n"
            #         "→ Must be exactly 10 digits (e.g., 9876543210)\n"
            #         "→ You entered: %s"
            #     ) % rec.director_phone)

            # One2many: Directors Detail
            for idx, line in enumerate(rec.directors_detail, start=1):
                if line.contact_no and not phone_pattern.fullmatch(line.contact_no):
                    raise ValidationError(_(
                        "Invalid Contact Number in Director Details (Row %d):\n"
                        "→ Name: %s\n"
                        "→ Must be exactly 10 digits\n"
                        "→ You entered: %s"
                    ) % (idx, line.name or "N/A", line.contact_no))

            # One2many: Address Detail
            for idx, addr in enumerate(rec.address_detail, start=1):
                if addr.business_phone and not phone_pattern.fullmatch(addr.business_phone):
                    raise ValidationError(_(
                        "Invalid Contact Number in Business Address (Row %d):\n"
                        "→ City: %s\n"
                        "→ Must be exactly 10 digits\n"
                        "→ You entered: %s"
                    ) % (idx, addr.business_city or "N/A", addr.business_phone))

    @api.constrains('email', 'directors_detail', 'address_detail')
    def _check_email_format(self):
        email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$')
        for rec in self:
            # Main Email
            if rec.email and not email_pattern.match(rec.email):
                raise ValidationError(_(
                    "The email in field [Email] is invalid:\n→ %s\nPlease enter a valid email like user@example.com."
                ) % rec.email)

            # Director Email
            # if rec.director_email and not email_pattern.match(rec.director_email):
            #     raise ValidationError(_(
            #         "The email in field [Director Email] is invalid:\n→ %s\nPlease enter a valid email like user@example.com."
            #     ) % rec.director_email)

            # One2many: Director Detail Emails
            for idx, line in enumerate(rec.directors_detail, 1):
                if line.email and not email_pattern.match(line.email):
                    raise ValidationError(_(
                        "Invalid email in [Director Details] row %s (Name: %s):\n→ %s\nExpected format: user@example.com."
                    ) % (idx, line.name or 'N/A', line.email))

            # One2many: Address Detail Emails
            for idx, addr in enumerate(rec.address_detail, 1):
                if addr.business_email and not email_pattern.match(addr.business_email):
                    raise ValidationError(_(
                        "Invalid email in [Address Details] row %s (City: %s):\n→ %s\nExpected format: user@example.com."
                    ) % (idx, addr.business_city or 'N/A', addr.business_email))

    @api.constrains('address_detail')
    def _check_pincode_format(self):
        pincode_pattern = re.compile(r'^\d{6}$')  # Indian pincode: exactly 6 digits
        for rec in self:
            if rec.is_overseas:
                continue  # Overseas addresses use country-specific postcode formats
            for idx, addr in enumerate(rec.address_detail, start=1):
                if addr.business_pincode and not pincode_pattern.fullmatch(addr.business_pincode):
                    raise ValidationError(_(
                        "Invalid Pincode in Business Address (Row %d):\n"
                        "→ City: %s\n"
                        "→ Entered: %s\n"
                        "→ Pincode must be exactly 6 digits (e.g., 400001)"
                    ) % (idx,
                         addr.business_city or "N/A",
                         addr.business_pincode))

    @api.constrains('pan_no')
    def _check_pan_card_no_format(self):
        pan_pattern = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
        for rec in self:
            if rec.is_overseas:
                continue  # PAN is India-specific; overseas partners don't have PAN
            if rec.pan_no and not pan_pattern.match(rec.pan_no.upper()):
                raise ValidationError(
                    _("PAN Card Number must be in the format: 5 letters, 4 digits, and 1 letter (e.g., ABCDE1234F).")
                )

    @api.constrains('udyam_number')
    def _check_udyam_no_format(self):
        udyam_pattern = re.compile(r'^UDYAM-[A-Z]{2}-\d{2}-\d{7}$')

        for rec in self:
            if rec.is_overseas:
                continue  # Udyam is India-specific
            if rec.udyam_number and not udyam_pattern.match(rec.udyam_number.upper()):
                raise ValidationError(_(
                    "Invalid Udyam Certificate Number: '%s'.\nExpected format is UDYAM-XX-00-0000000 "
                    "(e.g., UDYAM-MH-12-1234567)."
                ) % rec.udyam_number)

    @api.constrains('gst_no')
    def _check_gst_no_format(self):
        gst_pattern = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
        for rec in self:
            if rec.is_overseas:
                continue  # GST is India-specific
            if rec.gst_no and not gst_pattern.match(rec.gst_no.upper()):
                raise ValidationError(_(
                    "Invalid GST Number: '%s'. It must follow the 15-character format (e.g., 27ABCDE1234F1Z5)."
                ) % rec.gst_no)

    # @api.constrains('comp_google_loc')
    # def _check_lat_long_format(self):
    #     pattern = re.compile(r'Lat\s*:\s*(-?\d+(\.\d+)?)[,\s]+Long\s*:\s*(-?\d+(\.\d+)?)', re.IGNORECASE)
    #     for rec in self:
    #         if rec.comp_google_loc:
    #             match = pattern.search(rec.comp_google_loc.strip())
    #             if not match:
    #                 raise ValidationError(_(
    #                     "Invalid format for Google Location.\nPlease use the format:\nLat : <value> Long: <value>\n"
    #                     "Example: Lat : 22.3511148 Long: 78.6677428"
    #                 ))
    #             lat = float(match.group(1))
    #             lon = float(match.group(3))
    #             if not (-90 <= lat <= 90 and -180 <= lon <= 180):
    #                 raise ValidationError(_(
    #                     "Latitude must be between -90 and 90.\nLongitude must be between -180 and 180.\n"
    #                     "Your input: Lat = %s, Long = %s"
    #                 ) % (lat, lon))

    @api.constrains('cin_no')
    def _check_cin_format(self):
        pattern = re.compile(r'^([LU])\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$')
        for rec in self:
            if rec.cin_no and not pattern.match(rec.cin_no.upper()):
                raise ValidationError(_(
                    "Invalid CIN Number: '%s'. Expected format is like 'L12345MH2020PLC123456'."
                ) % rec.cin_no)

    @api.onchange('is_same_trade_name', 'business_legal_name')
    def _onchange_trade_name_sync(self):
        for rec in self:
            if rec.is_same_trade_name:
                rec.business_trade_name = rec.business_legal_name
            else:
                rec.business_trade_name = False

    partner_id = fields.Many2one('res.partner', string='Contact', domain="[('id', '=', active_id)]", tracking=True)
    existing_kyc_id = fields.Many2one('res.partner.kyc.approval', string='Existing KYC Record', readonly=True)

    is_overseas = fields.Boolean(
        string='Is Overseas',
        compute='_compute_is_overseas',
        store=False,
        help="Mirrors partner's is_overseas flag. Controls which document fields are shown.",
    )

    @api.depends('partner_id')
    def _compute_is_overseas(self):
        for rec in self:
            rec.is_overseas = rec.partner_id.is_overseas if rec.partner_id else False

    email = fields.Char("Email", required=True, tracking=True)
    point_of_contact = fields.Char("Vendor POC", required=True, tracking=True)
    poc_user = fields.Many2one('res.users', string="Bora Purchase Manager", default=lambda self: self.env.user)
    business_legal_name = fields.Char("Business Legal Name", required=True)
    is_same_trade_name = fields.Boolean(string="If Trade Name is same as Legal Name",
                                        help="Tick if trade name is same as legal name")
    business_trade_name = fields.Char("Business Trade Name", required=True)
    const_business = fields.Selection([('Sole Proprietor', 'Sole Proprietor'),
                                       ('Partnership', 'Partnership'),
                                       ('Pvt Ltd Co.', 'Pvt Ltd Co.'),
                                       ('LLP', 'LLP'),
                                       ('HUF(Karta)', 'HUF(Karta)'),
                                       ('Other', 'Other'),
                                       ], string="Constitution of Business", required=True)
    # const_business = fields.Many2one('constitution.business', string="Constitution of Business", required=True)
    other_business = fields.Char("If Other, Specify?")
    ##### Partnership/PrivateCo./LLP
    no_partner_director = fields.Selection([('1', '1'),
                                            ('2', '2'),
                                            ('3', '3'),
                                            ('4', '4'),
                                            ('5', '5'),
                                            ('6', '6'),
                                            ('7', '7')], string="Number of Managing Partner / Directors", default='1')
    directors_detail = fields.One2many('director.detail', 'kyc_wizard_id', string="Directors Detail")
    # no_partner_director = fields.Many2one('number.partner.director', string="Number of Managing Partner / Directors")
    # director_name = fields.Char(string="Name of the Owner / Director")
    # director_phone = fields.Char(string="Contact Number")
    # director_email = fields.Char(string="Email Address")
    # aadhaar_card = fields.Binary(string="Aadhaar Card")
    # aadhaar_card_filename = fields.Char(readonly=True)
    # pan_card = fields.Binary(string="PAN Card")
    # pan_card_filename = fields.Char(readonly=True)
    aadhaar_pan_link = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Aadhar and PAN card linking?')
    gst_no = fields.Char(string="GST Number")
    udyam_number = fields.Char(string="Udyam Certificate Number")

    # ── Overseas KYC document fields ────────────────────────────────────────────
    company_reg_document = fields.Many2many(
        'ir.attachment', 'wiz_overseas_company_reg_rel', 'wizard_id', 'attachment_id',
        string="Company Registration / Trade License",
        help="Trade License (UAE/Dubai), Business Registration Certificate (Hong Kong), "
             "or equivalent country-specific proof of company registration.",
    )
    company_reg_doc_expiry = fields.Date(
        string="Trade License / Company Reg. Expiry Date",
        help="Expiry date of the Company Registration or Trade License document.",
    )
    authorized_person_id_document = fields.Many2many(
        'ir.attachment', 'wiz_overseas_auth_person_id_rel', 'wizard_id', 'attachment_id',
        string="Authorized Person Identity Proof",
        help="Emirates ID or Passport (UAE), HKID or Passport (Hong Kong), "
             "or equivalent government-issued ID of the authorized signatory/manager.",
    )
    authorized_person_id_expiry = fields.Date(
        string="Authorized Person ID Expiry Date",
        help="Expiry date of the Authorized Person's identity document.",
    )
    license_registered = fields.Char(string="Any licenses registered (As per Local/State Government requirements)")
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rel', 'wizard_id', 'attachment_id',
                                       string="GST Certificate(Latest)", required=True)

    udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rel', 'wizard_id', 'attachment_id',
                                      string="Udyam Documents", required=False)
    shop_act_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_act_documents_rel', 'wizard_id',
                                         'attachment_id',
                                         string="Shop Act documents", required=False)

    gst_return_duration = fields.Selection([('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')],
                                           required=False, string="Filing Frequency")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Photos", required=True,
                                   help="Short Photos")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Videos", required=True,
                                   help="Short Video")
    bank_detail = fields.One2many('bank.detail', 'kyc_wizard_id', string="Bank Detail")
    address_detail = fields.One2many('address.detail', 'kyc_wizard_id', string="Address Detail")
    pan_no = fields.Char(string="PAN Number(Company)")
    pan_card_document = fields.Many2many('ir.attachment', 'pan_card_company_documents_rel', 'wizard_id',
                                         'attachment_id',
                                         string="PAN Card Document(Company)")
    incorporation_certificate = fields.Many2many('ir.attachment', 'incorportaion_certificate_rel', 'wizard_id',
                                                 'attachment_id',
                                                 string="Incorporation Certificate")
    comp_google_loc = fields.Char(string="GPS Location of Shop")

    partner_llp_filename = fields.Char()
    partner_llp = fields.Binary(string="Partnership Deed or LLP Deed")
    moa_aoa = fields.Many2many('ir.attachment', 'vendor_kyc_moa_aoa_rel', 'wizard_id', 'attachment_id',
                               string="MOA or AOA")
    cin_no = fields.Char(string="CIN number")
    electricity_bill = fields.Many2many('ir.attachment', 'vendor_kyc_electricity_bill_rel', 'wizard_id',
                                        'attachment_id',
                                        string="Electricity bill", required=False)

    #####
    @api.constrains('address_detail')
    def _check_minimum_address(self):
        for rec in self:
            if not rec.address_detail:
                raise ValidationError(_("Please add at least one address detail."))

    @api.constrains('bank_detail')
    def _check_minimum_bank(self):
        for rec in self:
            if not rec.bank_detail:
                raise ValidationError(_("Please add at least one bank detail."))

    @api.constrains('no_partner_director', 'directors_detail')
    def _check_director_limit(self):
        for rec in self:
            if rec.no_partner_director:
                expected = int(rec.no_partner_director)
                actual = len(rec.directors_detail)
                if actual != expected:
                    raise ValidationError(
                        _("You must add exactly %s director(s). You have added %s.") % (expected, actual)
                    )

    @api.model
    def default_get(self, fields):
        values = super().default_get(fields)
        res_id = self._context.get('active_id')
        res_model = self._context.get('active_model')
        is_rekyc = self._context.get('is_rekyc', False)
        default_partner_id = self._context.get('default_partner_id')
        
        # Get partner - either from context or from active record
        partner = None
        if default_partner_id:
            # Partner ID directly in context (from Re-KYC wizard)
            partner = self.env['res.partner'].browse(default_partner_id)
        elif res_id and res_model:
            record = self.env[res_model].browse(res_id)
            # If record is a partner, use it directly
            if res_model == 'res.partner':
                partner = record
            # If record is rekyc.request.wizard, get partner from it
            elif res_model == 'rekyc.request.wizard' and hasattr(record, 'partner_id'):
                partner = record.partner_id
        
        # Update values from partner if found
        if partner:
            values.update(
                email=partner.email or '',
                gst_no=partner.vat or '',
                pan_no=partner.l10n_in_pan or '',
            )
            
            # If Re-KYC, pre-fill from existing KYC record
            if is_rekyc:
                existing_kyc = self.env['res.partner.kyc.approval'].search([
                    ('partner_id', '=', partner.id)
                ], order='create_date desc', limit=1)
                
                if existing_kyc:
                    # Pre-fill all main fields from existing KYC
                    kyc_fields = [
                        'email', 'point_of_contact', 'business_legal_name',
                        'is_same_trade_name', 'business_trade_name', 'const_business',
                        'other_business', 'aadhaar_pan_link', 'gst_no', 'license_registered',
                        'udyam_number', 'gst_return_duration', 'pan_no', 'comp_google_loc',
                        'partner_llp', 'cin_no', 'no_partner_director'
                    ]
                    
                    for field in kyc_fields:
                        if field in fields and hasattr(existing_kyc, field):
                            value = getattr(existing_kyc, field)
                            if value:
                                values[field] = value
                    
                    # Handle poc_user separately (Many2one field - need to convert to ID)
                    if 'poc_user' in fields and existing_kyc.poc_user:
                        values['poc_user'] = existing_kyc.poc_user.id
                    
                    # Pre-fill Many2many attachment fields
                    attachment_fields = [
                        'gst_certificate', 'udyam_document', 'shop_act_document',
                        'shop_photos', 'shop_videos', 'pan_card_document',
                        'incorporation_certificate', 'moa_aoa', 'electricity_bill',
                        'company_reg_document', 'authorized_person_id_document',
                    ]

                    for field in attachment_fields:
                        if field in fields and hasattr(existing_kyc, field):
                            attachments = getattr(existing_kyc, field)
                            if attachments:
                                values[field] = [(6, 0, attachments.ids)]

                    # Pre-fill overseas document expiry dates
                    if existing_kyc.company_reg_doc_expiry:
                        values['company_reg_doc_expiry'] = existing_kyc.company_reg_doc_expiry
                    if existing_kyc.authorized_person_id_expiry:
                        values['authorized_person_id_expiry'] = existing_kyc.authorized_person_id_expiry

                    # Pre-fill One2many fields (directors, banks, addresses)
                    if 'directors_detail' in fields and existing_kyc.directors_detail:
                        directors_data = []
                        for director in existing_kyc.directors_detail:
                            dir_vals = {
                                'name': director.name,
                                'designation': director.designation,
                                'contact_no': director.contact_no,
                                'email': director.email,
                            }
                            # Add attachments if they exist
                            if director.aadhaar_card_attachments:
                                dir_vals['aadhaar_card_attachments'] = [(6, 0, director.aadhaar_card_attachments.ids)]
                            if director.pan_card_attachments:
                                dir_vals['pan_card_attachments'] = [(6, 0, director.pan_card_attachments.ids)]
                            if director.govt_id_attachments:
                                dir_vals['govt_id_attachments'] = [(6, 0, director.govt_id_attachments.ids)]
                            if director.govt_id_expiry:
                                dir_vals['govt_id_expiry'] = director.govt_id_expiry
                            directors_data.append((0, 0, dir_vals))
                        values['directors_detail'] = directors_data
                    
                    if 'bank_detail' in fields and existing_kyc.bank_detail:
                        bank_data = []
                        for bank in existing_kyc.bank_detail:
                            bank_vals = {
                                'bank_name': bank.bank_name,
                                'account_no': bank.account_no,
                                'ifsc_code': bank.ifsc_code,
                                # 'bank_address': bank.bank_address,
                            }
                            if bank.bank_cheque_attachments:
                                bank_vals['bank_cheque_attachments'] = [(6, 0, bank.bank_cheque_attachments.ids)]
                            bank_data.append((0, 0, bank_vals))
                        values['bank_detail'] = bank_data
                    
                    if 'address_detail' in fields and existing_kyc.address_detail:
                        address_data = []
                        for addr in existing_kyc.address_detail:
                            address_data.append((0, 0, {
                                'business_street': addr.business_street,
                                'business_city': addr.business_city,
                                'business_pincode': addr.business_pincode,
                                'business_phone': addr.business_phone,
                                'business_email': addr.business_email,
                                'business_state_id': addr.business_state_id.id if addr.business_state_id else False,
                                'business_country_id': addr.business_country_id.id if addr.business_country_id else False,
                            }))
                        values['address_detail'] = address_data
                    
                    # Store existing KYC ID for update
                    values['existing_kyc_id'] = existing_kyc.id
        
        return values

    # @api.onchange('const_business')
    # def _onchange_const_business_clear_fields(self):
    #     # Clear simple fields
    #     for field in [
    #         'other_business',
    #         'director_name',
    #         'director_phone',
    #         'director_email',
    #         'aadhaar_card',
    #         'pan_card'
    #     ]:
    #         setattr(self, field, False)

    def action_vendor_kyc_done(self):
        self.ensure_one()

        if not self.partner_id:
            return

        def prepare_one2many(lines, fields_map, many2many_fields=None):
            result = []
            many2many_fields = many2many_fields or []
            for line in lines:
                item = {}
                for target_field, source_field in fields_map.items():
                    value = getattr(line, source_field)
                    # Convert M2O records to their ID
                    if isinstance(value, models.BaseModel):
                        # Handle recordset - get ID if exists, else False
                        item[target_field] = value.id if value else False
                    elif value is None:
                        item[target_field] = False
                    else:
                        item[target_field] = value
                for m2m_field in many2many_fields:
                    attachments = getattr(line, m2m_field, False)
                    if attachments:
                        item[m2m_field] = [(6, 0, attachments.ids)]
                    else:
                        item[m2m_field] = [(5, 0, 0)]  # Remove all
                result.append((0, 0, item))
            return result

        # Prepare related data
        directors_data = prepare_one2many(
            self.directors_detail,
            fields_map={
                'name': 'name',
                'designation': 'designation',
                'contact_no': 'contact_no',
                'email': 'email',
                'govt_id_expiry': 'govt_id_expiry',
            },
            many2many_fields=['aadhaar_card_attachments', 'pan_card_attachments', 'govt_id_attachments']
        )

        bank_data = prepare_one2many(
            self.bank_detail,
            fields_map={
                'bank_name': 'bank_name',
                'account_no': 'account_no',
                'ifsc_code': 'ifsc_code',
                # 'bank_address': 'bank_address',
            },
            many2many_fields=['bank_cheque_attachments']
        )

        address_data = prepare_one2many(
            self.address_detail,
            fields_map={
                'business_street': 'business_street',
                'business_city': 'business_city',
                'business_pincode': 'business_pincode',
                'business_phone': 'business_phone',
                'business_email': 'business_email',
                'business_state_id': 'business_state_id',
                'business_country_id': 'business_country_id',

            }
        )

        directors_payload = []
        for line in self.directors_detail:
            directors_payload.append({
                'designation': line.designation or '',
                'name': line.name or '',
                'contact_no': line.contact_no or '',
                'email': line.email or '',
                'aadhaar_card_attachments': sorted(line.aadhaar_card_attachments.ids),
                'pan_card_attachments': sorted(line.pan_card_attachments.ids),
                'govt_id_attachments': sorted(line.govt_id_attachments.ids),
                'govt_id_expiry': str(line.govt_id_expiry) if line.govt_id_expiry else '',
            })

        bank_payload = []
        for line in self.bank_detail:
            bank_payload.append({
                'bank_name': line.bank_name or '',
                'account_no': line.account_no or '',
                'ifsc_code': line.ifsc_code or '',
                # 'bank_address': line.bank_address or '',
                'bank_cheque_attachments': sorted(line.bank_cheque_attachments.ids),
            })

        address_payload = []
        for line in self.address_detail:
            address_payload.append({
                'business_street': line.business_street or '',
                'business_city': line.business_city or '',
                'business_pincode': line.business_pincode or '',
                'business_phone': line.business_phone or '',
                'business_email': line.business_email or '',
                'business_state_id': line.business_state_id.id if line.business_state_id else False,
                'business_country_id': line.business_country_id.id if line.business_country_id else False,
            })

        # Prepare main record values
        kyc_vals = {
            'partner_id': self.partner_id.id if self.partner_id else False,
            'email': self.email,
            'point_of_contact': self.point_of_contact,
            'poc_user': self.poc_user.id if self.poc_user else False,
            'business_legal_name': self.business_legal_name,
            'is_same_trade_name': self.is_same_trade_name,
            'business_trade_name': self.business_trade_name,
            'address_detail': address_data,
            'const_business': self.const_business,
            'other_business': self.other_business,
            # 'director_name': self.director_name,
            # 'director_phone': self.director_phone,
            # 'director_email': self.director_email,
            # 'aadhaar_card': self.aadhaar_card,
            # 'aadhaar_card_filename': self.aadhaar_card_filename,
            # 'pan_card': self.pan_card,
            # 'pan_card_filename': self.pan_card_filename,
            'gst_no': self.gst_no,
            'license_registered': self.license_registered,
            'aadhaar_pan_link': self.aadhaar_pan_link,
            'udyam_number': self.udyam_number,
            'no_partner_director': self.no_partner_director,
            'directors_detail': directors_data,
            'pan_no': self.pan_no,
            'comp_google_loc': self.comp_google_loc,
            'partner_llp': self.partner_llp,
            'moa_aoa': [(6, 0, self.moa_aoa.ids)] if self.moa_aoa else [(5, 0, 0)],
            'cin_no': self.cin_no,
            'electricity_bill': [(6, 0, self.electricity_bill.ids)] if self.electricity_bill else [(5, 0, 0)],
            'pan_card_document': [(6, 0, self.pan_card_document.ids)] if self.pan_card_document else [(5, 0, 0)],
            'incorporation_certificate': [(6, 0, self.incorporation_certificate.ids)] if self.incorporation_certificate else [(5, 0, 0)],
            'gst_certificate': [(6, 0, self.gst_certificate.ids)] if self.gst_certificate else [(5, 0, 0)],
            'udyam_document': [(6, 0, self.udyam_document.ids)] if self.udyam_document else [(5, 0, 0)],
            'shop_act_document': [(6, 0, self.shop_act_document.ids)] if self.shop_act_document else [(5, 0, 0)],
            'gst_return_duration': self.gst_return_duration,
            'shop_photos': [(6, 0, self.shop_photos.ids)] if self.shop_photos else [(5, 0, 0)],
            'shop_videos': [(6, 0, self.shop_videos.ids)] if self.shop_videos else [(5, 0, 0)],
            'bank_detail': bank_data,
            # Overseas KYC documents (empty for Indian partners)
            'company_reg_document': [(6, 0, self.company_reg_document.ids)] if self.company_reg_document else [(5, 0, 0)],
            'company_reg_doc_expiry': self.company_reg_doc_expiry or False,
            'authorized_person_id_document': [(6, 0, self.authorized_person_id_document.ids)] if self.authorized_person_id_document else [(5, 0, 0)],
            'authorized_person_id_expiry': self.authorized_person_id_expiry or False,
        }
        
        # Check if this is Re-KYC (update existing record) or new KYC (create new record)
        if self.existing_kyc_id:
            kyc_record = self.existing_kyc_id

            if self.is_overseas:
                # ── Overseas Re-KYC: directly write changes to the KYC record ──────
                # Bypasses the pending-approval flow because:
                #   1. poc_user may be unset on survey-created records
                #   2. KYC state may not be 'confirmed'
                #   3. Overseas-specific fields (company_reg_document, govt_id_attachments)
                #      are not covered by the India-oriented change-detection logic
                for director in kyc_record.directors_detail:
                    director.write({
                        'aadhaar_card_attachments': [(5,)],
                        'pan_card_attachments': [(5,)],
                        'govt_id_attachments': [(5,)],
                    })
                for bank in kyc_record.bank_detail:
                    bank.write({'bank_cheque_attachments': [(5,)]})

                update_vals = dict(kyc_vals)
                update_vals['directors_detail'] = [(5, 0, 0)] + directors_data
                update_vals['bank_detail'] = [(5, 0, 0)] + bank_data
                update_vals['address_detail'] = [(5, 0, 0)] + address_data
                kyc_record.write(update_vals)

                self.partner_id.write({
                    'is_kyc': True,
                    'rejection_date': False,
                    'rejection_reason': False,
                    'is_rejected': False,
                })
            else:
                # ── Indian vendor Re-KYC: submit for POC approval ─────────────────
                payload = {
                    'email': self.email or '',
                    'point_of_contact': self.point_of_contact or '',
                    'poc_user': self.poc_user.id if self.poc_user else False,
                    'business_legal_name': self.business_legal_name or '',
                    'is_same_trade_name': bool(self.is_same_trade_name),
                    'business_trade_name': self.business_trade_name or '',
                    'const_business': self.const_business or '',
                    'other_business': self.other_business or '',
                    'aadhaar_pan_link': self.aadhaar_pan_link or '',
                    'gst_no': self.gst_no or '',
                    'license_registered': self.license_registered or '',
                    'udyam_number': self.udyam_number or '',
                    'gst_return_duration': self.gst_return_duration or '',
                    'pan_no': self.pan_no or '',
                    'comp_google_loc': self.comp_google_loc or '',
                    'partner_llp': self.partner_llp.decode() if isinstance(self.partner_llp, bytes) else (self.partner_llp or False),
                    'cin_no': self.cin_no or '',
                    'no_partner_director': self.no_partner_director or '',
                    'moa_aoa': sorted(self.moa_aoa.ids),
                    'electricity_bill': sorted(self.electricity_bill.ids),
                    'pan_card_document': sorted(self.pan_card_document.ids),
                    'incorporation_certificate': sorted(self.incorporation_certificate.ids),
                    'gst_certificate': sorted(self.gst_certificate.ids),
                    'udyam_document': sorted(self.udyam_document.ids),
                    'shop_act_document': sorted(self.shop_act_document.ids),
                    'shop_photos': sorted(self.shop_photos.ids),
                    'shop_videos': sorted(self.shop_videos.ids),
                    'directors_detail': directors_payload,
                    'bank_detail': bank_payload,
                    'address_detail': address_payload,
                    'company_reg_document': sorted(self.company_reg_document.ids),
                    'company_reg_doc_expiry': str(self.company_reg_doc_expiry) if self.company_reg_doc_expiry else '',
                    'authorized_person_id_document': sorted(self.authorized_person_id_document.ids),
                    'authorized_person_id_expiry': str(self.authorized_person_id_expiry) if self.authorized_person_id_expiry else '',
                }
                rekyc_remark = self._context.get('rekyc_remark', '')
                kyc_record.submit_rekyc_payload(payload, rekyc_remark)

            return {'type': 'ir.actions.act_window_close'}
        else:
            # New KYC: Create new record
            # Check if partner already has a KYC record to prevent duplicates
            existing_kyc = self.env['res.partner.kyc.approval'].search([
                ('partner_id', '=', self.partner_id.id)
            ], limit=1)
            
            if existing_kyc:
                raise ValidationError(_(
                    "A KYC record already exists for this partner. "
                    "Please use Re-KYC to update the existing record instead of creating a new one."
                ))
            
            kyc_record = self.env['res.partner.kyc.approval'].create(kyc_vals)

        # Link attachments to the new KYC record
        # attachment_fields = [
        #     self.gst_certificate,
        #     self.udyam_document,
        #     self.shop_act_document,
        #     self.shop_photos,
        #     self.electricity_bill,
        #     self.moa_aoa,
        #     self.pan_card_document,
        #     self.incorporation_certificate,
        #     self.shop_videos,
        # ]
        # all_attachments = sum((attachments for attachments in attachment_fields if attachments),
        #                       self.env['ir.attachment'])
        # if all_attachments:
        #     all_attachments.write({
        #         'res_model': 'res.partner.kyc.approval',
        #         'res_id': kyc_record.id,
        #     })
        #
        # # Link bank cheque attachments separately
        # for bank in kyc_record.bank_detail:
        #     if bank.bank_cheque_attachments:
        #         bank.bank_cheque_attachments.write({
        #             'res_model': 'res.partner.kyc.approval',
        #             'res_id': kyc_record.id,
        #         })

        # Update Partner
        if not self.partner_id.email and self.email:
            self.partner_id.email = self.email

        if not self.partner_id.vat and self.gst_no:
            self.partner_id.vat = self.gst_no

        if not self.partner_id.l10n_in_pan and self.pan_no:
            self.partner_id.l10n_in_pan = self.pan_no

        self.partner_id.write({
            'is_kyc': True,
            'rejection_date': False,
            'rejection_reason': False,
            'is_rejected': False,
        })

        return {'type': 'ir.actions.act_window_close'}


### Directors Details
class DirectorDetail(models.TransientModel):
    _name = "director.detail"
    _rec_name = 'name'
    _description = "Directors Detail"

    kyc_wizard_id = fields.Many2one('vendor.kyc.wizard', string="KYC Approval")
    designation = fields.Char(string="Designation", required=True)
    name = fields.Char(string="Name", required=True)
    contact_no = fields.Char(string="Contact Number", required=True)
    email = fields.Char(string="E-mail", required=True)
    aadhaar_card = fields.Binary(string="Aadhaar Card", required=False)
    aadhaar_card_filename = fields.Char()
    pan_card = fields.Binary(string="PAN Card", required=False)
    pan_card_filename = fields.Char()
    aadhaar_card_attachments = fields.Many2many('ir.attachment', 'wizard_aadhaar_card_rel', 'kyc_wizard_id',
                                                'attachment_id', string="Aadhaar Card")
    pan_card_attachments = fields.Many2many(
        'ir.attachment',
        'wizard_pan_card_rel', 'kyc_wizard_id',
        'attachment_id',
        string="PAN Card",
    )
    # Overseas: government-issued ID (Passport, Emirates ID, HKID, etc.)
    govt_id_attachments = fields.Many2many(
        'ir.attachment',
        'wizard_director_govt_id_rel', 'kyc_wizard_id',
        'attachment_id',
        string="Govt. ID (Passport / Emirates ID / HKID)",
    )
    govt_id_expiry = fields.Date(
        string="Govt. ID Expiry Date",
        help="Expiry date of this director's government-issued identity document.",
    )

    @api.constrains('aadhaar_card_attachments', 'pan_card_attachments')
    def _check_director_files(self):
        max_count = 1
        max_size = 10 * 1024 * 1024  # 10 MB
        for rec in self:
            # Aadhaar
            # if len(rec.aadhaar_card_attachments) > max_count:
            #     raise ValidationError("Only 1 Aadhaar Card file is allowed.")
            for att in rec.aadhaar_card_attachments:
                if att.file_size and att.file_size > max_size:
                    raise ValidationError("Aadhaar Card must be ≤ 10 MB.")

            # PAN
            # if len(rec.pan_card_attachments) > max_count:
            #     raise ValidationError("Only 1 PAN Card file is allowed.")
            for att in rec.pan_card_attachments:
                if att.file_size and att.file_size > max_size:
                    raise ValidationError("PAN Card must be ≤ 10 MB.")

    # @api.constrains('aadhaar_card', 'pan_card')
    # def _check_director_file_size(self):
    #     max_size = 10 * 1024 * 1024  # 10 MB in bytes
    #     for rec in self:
    #         if rec.aadhaar_card:
    #             aadhaar_binary = base64.b64decode(rec.aadhaar_card)
    #             if len(aadhaar_binary) > max_size:
    #                 raise ValidationError("Aadhaar Card must be ≤ 10 MB.")
    #
    #         if rec.pan_card:
    #             pan_binary = base64.b64decode(rec.pan_card)
    #             if len(pan_binary) > max_size:
    #                 raise ValidationError("PAN Card must be ≤ 10 MB.")


##### Bank Details
class BankDetail(models.TransientModel):
    _name = "bank.detail"
    _rec_name = 'bank_name'
    _description = "Bank Detail"

    kyc_wizard_id = fields.Many2one('vendor.kyc.wizard', string="KYC Approval")
    bank_name = fields.Char(string="Bank Name", required=True)
    account_no = fields.Char(string="Account Number", required=True)
    ifsc_code = fields.Char(string="IFSC Code", required=True)
    # bank_address = fields.Char(string="Bank Address",)
    bank_cheque_attachments = fields.Many2many('ir.attachment', 'wizard_bank_detail_cheque_rel', 'kyc_wizard_id',
                                               'attachment_id', string="Cancelled Cheques", required=True)

    @api.constrains('account_no', 'ifsc_code')
    def _check_account_and_ifsc(self):
        account_pattern = re.compile(r'^\d{9,18}$')  # Only digits, 9 to 18 characters
        ifsc_pattern = re.compile(r'^[A-Z]{4}0[0-9A-Z]{6}$')  # Standard IFSC format

        for rec in self:
            if not account_pattern.fullmatch(rec.account_no or ''):
                raise ValidationError(_(
                    "Invalid Bank Account Number:\n"
                    "→ Must be 9 to 18 digits only.\n"
                    "→ You entered: %s"
                ) % (rec.account_no or ''))

            if not ifsc_pattern.fullmatch((rec.ifsc_code or '').upper()):
                raise ValidationError(_(
                    "Invalid IFSC Code:\n"
                    "→ Must follow format: 4 letters, 0, then 6 digits (e.g., SBIN0001234)\n"
                    "→ You entered: %s"
                ) % (rec.ifsc_code or ''))

    @api.constrains('bank_cheque_attachments')
    def _check_cheque_files(self):
        max_count = 1
        max_size = 10 * 1024 * 1024
        for rec in self:
            # if len(rec.bank_cheque_attachments) > max_count:
            #     raise ValidationError("Only 1 Cancelled Cheque file is allowed.")
            for att in rec.bank_cheque_attachments:
                if att.file_size and att.file_size > max_size:
                    raise ValidationError("Cancelled Cheque must be ≤ 10 MB.")


##### Principal Place of Business
class AddressDetail(models.TransientModel):
    _name = "address.detail"
    _description = "Address Detail"

    kyc_wizard_id = fields.Many2one('vendor.kyc.wizard', string="KYC Approval")
    business_street = fields.Char("Address", required=True)
    business_city = fields.Char("City", required=True)
    business_pincode = fields.Char("Pincode", required=True)
    business_phone = fields.Char("Contact Number", required=True)
    business_email = fields.Char("Email", required=True)
    business_state_id = fields.Many2one('res.country.state', string='State',
                                        domain="[('country_id', '=?', business_country_id)]")
    business_country_id = fields.Many2one('res.country', string='Country')

    @api.onchange('business_country_id')
    def _onchange_country_id(self):
        for rec in self:
            # Clear the state if it doesn't belong to the selected country
            if rec.business_state_id and rec.business_state_id.country_id != rec.business_country_id:
                rec.business_state_id = False

    @api.onchange('business_state_id')
    def _onchange_state_id(self):
        for rec in self:
            # Automatically set country based on state
            if rec.business_state_id:
                rec.business_country_id = rec.business_state_id.country_id

# # -*- coding: utf-8 -*-
#
# import base64
# import re
# from odoo.exceptions import ValidationError
#
# from odoo import api, fields, models, _
#
#
# class VendorKycWizard(models.TransientModel):
#     _name = 'vendor.kyc.wizard'
#     _description = 'Vendor KYC Wizard'
#
#     @api.constrains('gst_certificate', 'udyam_document', 'shop_act_document', 'shop_photos', 'shop_videos',
#                     'pan_card_document', 'incorporation_certificate', 'moa_aoa', 'electricity_bill')
#     def _check_attachment_limits(self):
#         limits = {
#             'gst_certificate': (1, 10 * 1024 * 1024),
#             'udyam_document': (1, 10 * 1024 * 1024),
#             'shop_act_document': (1, 10 * 1024 * 1024),
#             'shop_photos': (10, 100 * 1024 * 1024),
#             'shop_videos': (10, 100 * 1024 * 1024),
#             'pan_card_document': (1, 10 * 1024 * 1024),
#             'incorporation_certificate': (5, 10 * 1024 * 1024),
#             'moa_aoa': (5, 10 * 1024 * 1024),
#             'electricity_bill': (5, 10 * 1024 * 1024),
#         }
#         for field_name, (max_count, max_size) in limits.items():
#             attachments = getattr(self, field_name)
#             if len(attachments) > max_count:
#                 raise ValidationError(f"Only {max_count} file(s) allowed for '{self._fields[field_name].string}'.")
#             for attachment in attachments:
#                 if attachment.file_size and attachment.file_size > max_size:
#                     raise ValidationError(
#                         f"Each file in '{self._fields[field_name].string}' must be ≤ {max_size // (1024 * 1024)} MB."
#                     )
#
#     @api.constrains('partner_llp')
#     def _check_partner_llp_size(self):
#         max_size = 10 * 1024 * 1024  # 10 MB
#
#         for rec in self:
#             if rec.partner_llp:
#                 try:
#                     decoded_size = len(base64.b64decode(rec.partner_llp))
#                     if decoded_size > max_size:
#                         raise ValidationError(_("Partner LLP document exceeds the maximum size of 10 MB."))
#                 except Exception:
#                     raise ValidationError(_("Invalid Partner LLP file format."))
#
#     @api.constrains('directors_detail', 'address_detail')
#     def _check_phone_numbers(self):
#         phone_pattern = re.compile(r'^[0-9]{10}$')  # Validates 10-digit numbers
#
#         for rec in self:
#
#             # One2many: Directors Detail
#             for idx, line in enumerate(rec.directors_detail, start=1):
#                 if line.contact_no and not phone_pattern.fullmatch(line.contact_no):
#                     raise ValidationError(_(
#                         "Invalid Contact Number in Director Details (Row %d):\n"
#                         "→ Name: %s\n"
#                         "→ Must be exactly 10 digits\n"
#                         "→ You entered: %s"
#                     ) % (idx, line.name or "N/A", line.contact_no))
#
#             # One2many: Address Detail
#             for idx, addr in enumerate(rec.address_detail, start=1):
#                 if addr.business_phone and not phone_pattern.fullmatch(addr.business_phone):
#                     raise ValidationError(_(
#                         "Invalid Contact Number in Business Address (Row %d):\n"
#                         "→ City: %s\n"
#                         "→ Must be exactly 10 digits\n"
#                         "→ You entered: %s"
#                     ) % (idx, addr.business_city or "N/A", addr.business_phone))
#
#     @api.constrains('email', 'directors_detail', 'address_detail')
#     def _check_email_format(self):
#         email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$')
#         for rec in self:
#             # Main Email
#             if rec.email and not email_pattern.match(rec.email):
#                 raise ValidationError(_(
#                     "The email in field [Email] is invalid:\n→ %s\nPlease enter a valid email like user@example.com."
#                 ) % rec.email)
#
#             # Director Email
#
#             # One2many: Director Detail Emails
#             for idx, line in enumerate(rec.directors_detail, 1):
#                 if line.email and not email_pattern.match(line.email):
#                     raise ValidationError(_(
#                         "Invalid email in [Director Details] row %s (Name: %s):\n→ %s\nExpected format: user@example.com."
#                     ) % (idx, line.name or 'N/A', line.email))
#
#             # One2many: Address Detail Emails
#             for idx, addr in enumerate(rec.address_detail, 1):
#                 if addr.business_email and not email_pattern.match(addr.business_email):
#                     raise ValidationError(_(
#                         "Invalid email in [Address Details] row %s (City: %s):\n→ %s\nExpected format: user@example.com."
#                     ) % (idx, addr.business_city or 'N/A', addr.business_email))
#
#     @api.constrains('address_detail')
#     def _check_pincode_format(self):
#         pincode_pattern = re.compile(r'^\d{6}$')  # Indian pincode: exactly 6 digits
#         for rec in self:
#             for idx, addr in enumerate(rec.address_detail, start=1):
#                 if addr.business_pincode and not pincode_pattern.fullmatch(addr.business_pincode):
#                     raise ValidationError(_(
#                         "Invalid Pincode in Business Address (Row %d):\n"
#                         "→ City: %s\n"
#                         "→ Entered: %s\n"
#                         "→ Pincode must be exactly 6 digits (e.g., 400001)"
#                     ) % (idx,
#                          addr.business_city or "N/A",
#                          addr.business_pincode))
#
#     @api.constrains('pan_no')
#     def _check_pan_card_no_format(self):
#         pan_pattern = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
#         for rec in self:
#             if rec.pan_no and not pan_pattern.match(rec.pan_no.upper()):
#                 raise ValidationError(
#                     _("PAN Card Number must be in the format: 5 letters, 4 digits, and 1 letter (e.g., ABCDE1234F).")
#                 )
#
#     @api.constrains('udyam_number')
#     def _check_udyam_no_format(self):
#         udyam_pattern = re.compile(r'^UDYAM-[A-Z]{2}-\d{2}-\d{7}$')
#
#         for rec in self:
#             if rec.udyam_number and not udyam_pattern.match(rec.udyam_number.upper()):
#                 raise ValidationError(_(
#                     "Invalid Udyam Certificate Number: '%s'.\nExpected format is UDYAM-XX-00-0000000 "
#                     "(e.g., UDYAM-MH-12-1234567)."
#                 ) % rec.udyam_number)
#
#     @api.constrains('gst_no')
#     def _check_gst_no_format(self):
#         gst_pattern = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
#         for rec in self:
#             if rec.gst_no and not gst_pattern.match(rec.gst_no.upper()):
#                 raise ValidationError(_(
#                     "Invalid GST Number: '%s'. It must follow the 15-character format (e.g., 27ABCDE1234F1Z5)."
#                 ) % rec.gst_no)
#
#     @api.constrains('cin_no')
#     def _check_cin_format(self):
#         pattern = re.compile(r'^([LU])\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}$')
#         for rec in self:
#             if rec.cin_no and not pattern.match(rec.cin_no.upper()):
#                 raise ValidationError(_(
#                     "Invalid CIN Number: '%s'. Expected format is like 'L12345MH2020PLC123456'."
#                 ) % rec.cin_no)
#
#     @api.onchange('is_same_trade_name', 'business_legal_name')
#     def _onchange_trade_name_sync(self):
#         for rec in self:
#             if rec.is_same_trade_name:
#                 rec.business_trade_name = rec.business_legal_name
#             else:
#                 rec.business_trade_name = False
#
#     partner_id = fields.Many2one('res.partner', string='Contact', domain="[('id', '=', active_id)]", tracking=True)
#     email = fields.Char("Email", required=True, tracking=True)
#     point_of_contact = fields.Char("Point of Contact", required=True, tracking=True)
#     poc_user = fields.Many2one('res.users', string="Point of Contact to Vendor", default=lambda self: self.env.user,
#                                readonly=1)
#     business_legal_name = fields.Char("Business Legal Name", required=True)
#     is_same_trade_name = fields.Boolean(string="If Trade Name is same as Legal Name",
#                                         help="Tick if trade name is same as legal name")
#     business_trade_name = fields.Char("Business Trade Name", required=True)
#     const_business = fields.Selection([('Sole Proprietor', 'Sole Proprietor'),
#                                        ('Partnership', 'Partnership'),
#                                        ('Pvt Ltd Co.', 'Pvt Ltd Co.'),
#                                        ('LLP', 'LLP'),
#                                        ('HUF(Karta)', 'HUF(Karta)'),
#                                        ('Other', 'Other'),
#                                        ], string="Constitution of Business", required=True)
#     # const_business = fields.Many2one('constitution.business', string="Constitution of Business", required=True)
#     other_business = fields.Char("If Other, Specify?")
#     # Partnership/PrivateCo./LLP
#     no_partner_director = fields.Selection([('1', '1'),
#                                             ('2', '2'),
#                                             ('3', '3'),
#                                             ('4', '4'),
#                                             ('5', '5'),
#                                             ('6', '6'),
#                                             ('7', '7')], string="Number of Managing Partner / Directors", default='1')
#     directors_detail = fields.One2many('director.detail', 'kyc_wizard_id', string="Directors Detail")
#
#     aadhaar_pan_link = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Aadhar and PAN card linking?',
#                                         required=True)
#     gst_no = fields.Char(string="GST Number", required=True)
#     udyam_number = fields.Char(string="Udyam Certificate Number", required=True)
#     license_registered = fields.Char(string="Any licenses registered (As per Local/State Government requirements)")
#     gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rel', 'wizard_id', 'attachment_id',
#                                        string="GST Certificate(Latest)", required=True)
#
#     udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rel', 'wizard_id', 'attachment_id',
#                                       string="Udyam Documents", required=False)
#     shop_act_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_act_documents_rel', 'wizard_id',
#                                          'attachment_id',
#                                          string="Shop Act documents", required=False)
#
#     gst_return_duration = fields.Selection([('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')],
#                                            required=False, string="GST Return duration")
#
#     shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rel', 'wizard_id', 'attachment_id',
#                                    string="Shop Photos", required=True,
#                                    help="Short Photos")
#
#     shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rel', 'wizard_id', 'attachment_id',
#                                    string="Shop Videos", required=True,
#                                    help="Short Video")
#     bank_detail = fields.One2many('bank.detail', 'kyc_wizard_id', string="Bank Detail")
#     address_detail = fields.One2many('address.detail', 'kyc_wizard_id', string="Address Detail")
#     pan_no = fields.Char(string="PAN Number(Company)", required=True)
#     pan_card_document = fields.Many2many('ir.attachment', 'pan_card_company_documents_rel', 'wizard_id',
#                                          'attachment_id',
#                                          string="PAN Card Document(Company)")
#     incorporation_certificate = fields.Many2many('ir.attachment', 'incorportaion_certificate_rel', 'wizard_id',
#                                                  'attachment_id',
#                                                  string="Incorporation Certificate")
#     comp_google_loc = fields.Char(string="Google Location of Shop", required=False)
#
#     partner_llp_filename = fields.Char()
#     partner_llp = fields.Binary(string="Partnership Deed or LLP Deed")
#     moa_aoa = fields.Many2many('ir.attachment', 'vendor_kyc_moa_aoa_rel', 'wizard_id', 'attachment_id',
#                                string="MOA or AOA")
#     cin_no = fields.Char(string="CIN number")
#     electricity_bill = fields.Many2many('ir.attachment', 'vendor_kyc_electricity_bill_rel', 'wizard_id',
#                                         'attachment_id',
#                                         string="Electricity bill", required=False)
#
#     #####
#     @api.constrains('address_detail')
#     def _check_minimum_address(self):
#         for rec in self:
#             if not rec.address_detail:
#                 raise ValidationError(_("Please add at least one address detail."))
#
#     @api.constrains('bank_detail')
#     def _check_minimum_bank(self):
#         for rec in self:
#             if not rec.bank_detail:
#                 raise ValidationError(_("Please add at least one bank detail."))
#
#     @api.constrains('no_partner_director', 'directors_detail')
#     def _check_director_limit(self):
#         for rec in self:
#             if rec.no_partner_director:
#                 expected = int(rec.no_partner_director)
#                 actual = len(rec.directors_detail)
#                 if actual != expected:
#                     raise ValidationError(
#                         _("You must add exactly %s director(s). You have added %s.") % (expected, actual)
#                     )
#
#     @api.model
#     def default_get(self, fields):
#         values = super().default_get(fields)
#         res_id = self._context.get('active_id')
#         res_model = self._context.get('active_model')
#         if res_id and res_model:
#             record = self.env[res_model].browse(res_id)
#             values.update(
#                 email=record.email,
#                 gst_no=record.vat,
#                 pan_no=record.l10n_in_pan,
#             )
#         return values
#
#     def action_vendor_kyc_done(self):
#         self.ensure_one()
#
#         if not self.partner_id:
#             return
#
#         def prepare_one2many(lines, fields_map, many2many_fields=None):
#             result = []
#             many2many_fields = many2many_fields or []
#             for line in lines:
#                 item = {}
#                 for target_field, source_field in fields_map.items():
#                     value = getattr(line, source_field)
#                     # Convert M2O records to their ID
#                     if isinstance(value, models.BaseModel):
#                         item[target_field] = value.id
#                     else:
#                         item[target_field] = value
#                 for m2m_field in many2many_fields:
#                     item[m2m_field] = [(6, 0, getattr(line, m2m_field).ids)]
#                 result.append((0, 0, item))
#             return result
#
#         # Prepare related data
#         directors_data = prepare_one2many(
#             self.directors_detail,
#             fields_map={
#                 'name': 'name',
#                 'designation': 'designation',
#                 'contact_no': 'contact_no',
#                 'email': 'email',
#                 # 'aadhaar_card': 'aadhaar_card',
#                 # 'pan_card': 'pan_card',
#             },
#             many2many_fields=['aadhaar_card_attachments', 'pan_card_attachments']
#         )
#
#         bank_data = prepare_one2many(
#             self.bank_detail,
#             fields_map={
#                 'bank_name': 'bank_name',
#                 'account_no': 'account_no',
#                 'ifsc_code': 'ifsc_code',
#                 'bank_address': 'bank_address',
#             },
#             many2many_fields=['bank_cheque_attachments']
#         )
#
#         address_data = prepare_one2many(
#             self.address_detail,
#             fields_map={
#                 'business_street': 'business_street',
#                 'business_city': 'business_city',
#                 'business_pincode': 'business_pincode',
#                 'business_phone': 'business_phone',
#                 'business_email': 'business_email',
#                 'business_state_id': 'business_state_id',
#                 'business_country_id': 'business_country_id',
#
#             }
#         )
#
#         # Prepare main record values
#         kyc_vals = {
#             'partner_id': self.partner_id.id,
#             'email': self.email,
#             'point_of_contact': self.point_of_contact,
#             'poc_user': self.poc_user.id,
#             'business_legal_name': self.business_legal_name,
#             'is_same_trade_name': self.is_same_trade_name,
#             'business_trade_name': self.business_trade_name,
#             'address_detail': address_data,
#             'const_business': self.const_business,
#             'other_business': self.other_business,
#             'gst_no': self.gst_no,
#             'license_registered': self.license_registered,
#             'aadhaar_pan_link': self.aadhaar_pan_link,
#             'udyam_number': self.udyam_number,
#             'no_partner_director': self.no_partner_director,
#             'directors_detail': directors_data,
#             'pan_no': self.pan_no,
#             'comp_google_loc': self.comp_google_loc,
#             'partner_llp': self.partner_llp,
#             'moa_aoa': [(6, 0, self.moa_aoa.ids)],
#             'cin_no': self.cin_no,
#             'electricity_bill': [(6, 0, self.electricity_bill.ids)],
#             'pan_card_document': [(6, 0, self.pan_card_document.ids)],
#             'incorporation_certificate': [(6, 0, self.incorporation_certificate.ids)],
#             'gst_certificate': [(6, 0, self.gst_certificate.ids)],
#             'udyam_document': [(6, 0, self.udyam_document.ids)],
#             'shop_act_document': [(6, 0, self.shop_act_document.ids)],
#             'gst_return_duration': self.gst_return_duration,
#             'shop_photos': [(6, 0, self.shop_photos.ids)],
#             'shop_videos': [(6, 0, self.shop_videos.ids)],
#             'bank_detail': bank_data,
#         }
#         # Create the KYC record
#         kyc_record = self.env['res.partner.kyc.approval'].create(kyc_vals)
#
#         # Update Partner
#         if not self.partner_id.email and self.email:
#             self.partner_id.email = self.email
#
#         if not self.partner_id.vat and self.gst_no:
#             self.partner_id.vat = self.gst_no
#
#         if not self.partner_id.l10n_in_pan and self.pan_no:
#             self.partner_id.l10n_in_pan = self.pan_no
#
#         self.partner_id.write({
#             'is_kyc': True,
#             'rejection_date': False,
#             'rejection_reason': False,
#             'is_rejected': False,
#         })
#
#         return {'type': 'ir.actions.act_window_close'}
#
#
# # Directors Details
# class DirectorDetail(models.TransientModel):
#     _name = "director.detail"
#     _rec_name = 'name'
#     _description = "Directors Detail"
#
#     kyc_wizard_id = fields.Many2one('vendor.kyc.wizard', string="KYC Approval")
#     designation = fields.Char(string="Designation", required=True)
#     name = fields.Char(string="Name", required=True)
#     contact_no = fields.Char(string="Contact Number", required=True)
#     email = fields.Char(string="E-mail", required=True)
#     aadhaar_card = fields.Binary(string="Aadhaar Card", required=False)
#     aadhaar_card_filename = fields.Char()
#     pan_card = fields.Binary(string="PAN Card", required=False)
#     pan_card_filename = fields.Char()
#     aadhaar_card_attachments = fields.Many2many('ir.attachment', 'wizard_aadhaar_card_rel', 'kyc_wizard_id',
#                                                 'attachment_id', string="Aadhaar Card", required=True)
#     pan_card_attachments = fields.Many2many(
#         'ir.attachment',
#         'wizard_pan_card_rel', 'kyc_wizard_id',
#         'attachment_id',
#         string="PAN Card",
#         required=True
#     )
#
#     @api.constrains('aadhaar_card_attachments', 'pan_card_attachments')
#     def _check_director_files(self):
#         max_count = 1
#         max_size = 10 * 1024 * 1024  # 10 MB
#         for rec in self:
#             # Aadhaar
#             if len(rec.aadhaar_card_attachments) > max_count:
#                 raise ValidationError("Only 1 Aadhaar Card file is allowed.")
#             for att in rec.aadhaar_card_attachments:
#                 if att.file_size and att.file_size > max_size:
#                     raise ValidationError("Aadhaar Card must be ≤ 10 MB.")
#
#             # PAN
#             if len(rec.pan_card_attachments) > max_count:
#                 raise ValidationError("Only 1 PAN Card file is allowed.")
#             for att in rec.pan_card_attachments:
#                 if att.file_size and att.file_size > max_size:
#                     raise ValidationError("PAN Card must be ≤ 10 MB.")
#
#
# # Bank Details
# class BankDetail(models.TransientModel):
#     _name = "bank.detail"
#     _rec_name = 'bank_name'
#     _description = "Bank Detail"
#
#     kyc_wizard_id = fields.Many2one('vendor.kyc.wizard', string="KYC Approval")
#     bank_name = fields.Char(string="Bank Name", required=True)
#     account_no = fields.Char(string="Account Number", required=True)
#     ifsc_code = fields.Char(string="IFSC Code", required=True)
#     bank_address = fields.Char(string="Bank Address", required=True)
#     bank_cheque_attachments = fields.Many2many('ir.attachment', 'wizard_bank_detail_cheque_rel', 'kyc_wizard_id',
#                                                'attachment_id', string="Cancelled Cheques", required=True)
#
#     @api.constrains('account_no', 'ifsc_code')
#     def _check_account_and_ifsc(self):
#         account_pattern = re.compile(r'^\d{9,18}$')  # Only digits, 9 to 18 characters
#         ifsc_pattern = re.compile(r'^[A-Z]{4}0[0-9A-Z]{6}$')  # Standard IFSC format
#
#         for rec in self:
#             if not account_pattern.fullmatch(rec.account_no or ''):
#                 raise ValidationError(_(
#                     "Invalid Bank Account Number:\n"
#                     "→ Must be 9 to 18 digits only.\n"
#                     "→ You entered: %s"
#                 ) % (rec.account_no or ''))
#
#             if not ifsc_pattern.fullmatch((rec.ifsc_code or '').upper()):
#                 raise ValidationError(_(
#                     "Invalid IFSC Code:\n"
#                     "→ Must follow format: 4 letters, 0, then 6 digits (e.g., SBIN0001234)\n"
#                     "→ You entered: %s"
#                 ) % (rec.ifsc_code or ''))
#
#     @api.constrains('bank_cheque_attachments')
#     def _check_cheque_files(self):
#         max_count = 1
#         max_size = 10 * 1024 * 1024
#         for rec in self:
#             if len(rec.bank_cheque_attachments) > max_count:
#                 raise ValidationError("Only 1 Cancelled Cheque file is allowed.")
#             for att in rec.bank_cheque_attachments:
#                 if att.file_size and att.file_size > max_size:
#                     raise ValidationError("Cancelled Cheque must be ≤ 10 MB.")
#
#
# # Principal Place of Business
# class AddressDetail(models.TransientModel):
#     _name = "address.detail"
#     _description = "Address Detail"
#
#     kyc_wizard_id = fields.Many2one('vendor.kyc.wizard', string="KYC Approval")
#     business_street = fields.Char("Address", required=True)
#     business_city = fields.Char("City", required=True)
#     business_pincode = fields.Char("Pincode", required=True)
#     business_phone = fields.Char("Contact Number", required=True)
#     business_email = fields.Char("Email", required=True)
#     business_state_id = fields.Many2one('res.country.state', string='State',
#                                         domain="[('country_id', '=?', business_country_id)]")
#     business_country_id = fields.Many2one('res.country', string='Country')
#
#     @api.onchange('business_country_id')
#     def _onchange_country_id(self):
#         for rec in self:
#             # Clear the state if it doesn't belong to the selected country
#             if rec.business_state_id and rec.business_state_id.country_id != rec.business_country_id:
#                 rec.business_state_id = False
#
#     @api.onchange('business_state_id')
#     def _onchange_state_id(self):
#         for rec in self:
#             # Automatically set country based on state
#             if rec.business_state_id:
#                 rec.business_country_id = rec.business_state_id.country_id
