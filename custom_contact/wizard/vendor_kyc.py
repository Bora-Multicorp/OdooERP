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
        limits = {
            'gst_certificate': (1, 10 * 1024 * 1024),
            'udyam_document': (1, 10 * 1024 * 1024),
            'shop_act_document': (1, 10 * 1024 * 1024),
            'shop_photos': (10, 100 * 1024 * 1024),
            'shop_videos': (10, 100 * 1024 * 1024),
            'pan_card_document': (1, 10 * 1024 * 1024),
            'incorporation_certificate': (5, 10 * 1024 * 1024),
            'moa_aoa': (5, 10 * 1024 * 1024),
            'electricity_bill': (5, 10 * 1024 * 1024),
        }
        for field_name, (max_count, max_size) in limits.items():
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
            if rec.pan_no and not pan_pattern.match(rec.pan_no.upper()):
                raise ValidationError(
                    _("PAN Card Number must be in the format: 5 letters, 4 digits, and 1 letter (e.g., ABCDE1234F).")
                )

    @api.constrains('udyam_number')
    def _check_udyam_no_format(self):
        udyam_pattern = re.compile(r'^UDYAM-[A-Z]{2}-\d{2}-\d{7}$')

        for rec in self:
            if rec.udyam_number and not udyam_pattern.match(rec.udyam_number.upper()):
                raise ValidationError(_(
                    "Invalid Udyam Certificate Number: '%s'.\nExpected format is UDYAM-XX-00-0000000 "
                    "(e.g., UDYAM-MH-12-1234567)."
                ) % rec.udyam_number)

    @api.constrains('gst_no')
    def _check_gst_no_format(self):
        gst_pattern = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
        for rec in self:
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

    partner_id = fields.Many2one('res.partner', string='Contact', domain="[('id', '=', active_id)]")
    email = fields.Char("Email", required=True)
    point_of_contact = fields.Char("Point of Contact", required=True)
    poc_user = fields.Many2one('res.users', string="Point of Contact to Vendor", default=lambda self: self.env.user,
                               readonly=1)
    business_legal_name = fields.Char("Business Legal Name", required=True)
    is_same_trade_name = fields.Boolean(string="If Trade Name is same as Legal Name", help="Tick if trade name is same as legal name")
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
    aadhaar_pan_link = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='Aadhar and PAN card linking?',
                                        required=True)
    gst_no = fields.Char(string="GST Number", required=True)
    udyam_number = fields.Char(string="Udyam Certificate Number", required=True)
    license_registered = fields.Char(string="Any licenses registered (As per Local/State Government requirements)")
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rel', 'wizard_id', 'attachment_id',
                                       string="GST Certificate(Latest)", required=True)

    udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rel', 'wizard_id', 'attachment_id',
                                      string="Udyam Documents", required=False)
    shop_act_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_act_documents_rel', 'wizard_id',
                                         'attachment_id',
                                         string="Shop Act documents", required=False)

    gst_return_duration = fields.Selection([('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')],
                                           required=False, string="GST Return duration")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Photos", required=True,
                                   help="Short Photos")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Videos", required=True,
                                   help="Short Video")
    bank_detail = fields.One2many('bank.detail', 'kyc_wizard_id', string="Bank Detail")
    address_detail = fields.One2many('address.detail', 'kyc_wizard_id', string="Address Detail")
    pan_no = fields.Char(string="PAN Number(Company)", required=True)
    pan_card_document = fields.Many2many('ir.attachment', 'pan_card_company_documents_rel', 'wizard_id',
                                         'attachment_id',
                                         string="PAN Card Document(Company)")
    incorporation_certificate = fields.Many2many('ir.attachment', 'incorportaion_certificate_rel', 'wizard_id',
                                                 'attachment_id',
                                                 string="Incorporation Certificate")
    comp_google_loc = fields.Char(string="Google Location of Shop", required=False)

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
        if res_id and res_model:
            record = self.env[res_model].browse(res_id)
            values.update(
                email=record.email,
                gst_no=record.vat,
                pan_no=record.l10n_in_pan,
            )
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
                        item[target_field] = value.id
                    else:
                        item[target_field] = value
                for m2m_field in many2many_fields:
                    item[m2m_field] = [(6, 0, getattr(line, m2m_field).ids)]
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
                # 'aadhaar_card': 'aadhaar_card',
                # 'pan_card': 'pan_card',
            },
            many2many_fields=['aadhaar_card_attachments', 'pan_card_attachments']
        )

        bank_data = prepare_one2many(
            self.bank_detail,
            fields_map={
                'bank_name': 'bank_name',
                'account_no': 'account_no',
                'ifsc_code': 'ifsc_code',
                'bank_address': 'bank_address',
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

        # Prepare main record values
        kyc_vals = {
            'partner_id': self.partner_id.id,
            'email': self.email,
            'point_of_contact': self.point_of_contact,
            'poc_user': self.poc_user.id,
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
            'moa_aoa': [(6, 0, self.moa_aoa.ids)],
            'cin_no': self.cin_no,
            'electricity_bill': [(6, 0, self.electricity_bill.ids)],
            'pan_card_document': [(6, 0, self.pan_card_document.ids)],
            'incorporation_certificate': [(6, 0, self.incorporation_certificate.ids)],
            'gst_certificate': [(6, 0, self.gst_certificate.ids)],
            'udyam_document': [(6, 0, self.udyam_document.ids)],
            'shop_act_document': [(6, 0, self.shop_act_document.ids)],
            'gst_return_duration': self.gst_return_duration,
            'shop_photos': [(6, 0, self.shop_photos.ids)],
            'shop_videos': [(6, 0, self.shop_videos.ids)],
            'bank_detail': bank_data,
        }
        # Create the KYC record
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
                                               'attachment_id', string="Aadhaar Card", required=True)
    pan_card_attachments = fields.Many2many(
        'ir.attachment',
        'wizard_pan_card_rel', 'kyc_wizard_id',
        'attachment_id',
        string="PAN Card",
        required=True
    )

    @api.constrains('aadhaar_card_attachments', 'pan_card_attachments')
    def _check_director_files(self):
        max_count = 1
        max_size = 10 * 1024 * 1024  # 10 MB
        for rec in self:
            # Aadhaar
            if len(rec.aadhaar_card_attachments) > max_count:
                raise ValidationError("Only 1 Aadhaar Card file is allowed.")
            for att in rec.aadhaar_card_attachments:
                if att.file_size and att.file_size > max_size:
                    raise ValidationError("Aadhaar Card must be ≤ 10 MB.")

            # PAN
            if len(rec.pan_card_attachments) > max_count:
                raise ValidationError("Only 1 PAN Card file is allowed.")
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
    bank_address = fields.Char(string="Bank Address", required=True)
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
            if len(rec.bank_cheque_attachments) > max_count:
                raise ValidationError("Only 1 Cancelled Cheque file is allowed.")
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
