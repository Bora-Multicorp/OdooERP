# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class VendorKycWizard(models.TransientModel):
    _name = 'vendor.kyc.wizard'
    _description = 'Vendor KYC Wizard'

    @api.constrains('director_phone', 'directors_detail', 'address_detail')
    def _check_phone_numbers(self):
        phone_pattern = re.compile(r'^[0-9]{10}$')  # Only 10-digit numbers
        for rec in self:
            # Wizard-level director phone
            if rec.director_phone and not phone_pattern.match(rec.director_phone):
                raise ValidationError(_(
                    "Director Contact Number must be exactly 10 digits (e.g., 9876543210).\n"
                    "Invalid Value: %s"
                ) % rec.director_phone)

            # One2many: Director Detail Contact Numbers
            for line in rec.directors_detail:
                if line.contact_no and not phone_pattern.match(line.contact_no):
                    raise ValidationError(_(
                        "Director Detail Contact Number must be exactly 10 digits.\n"
                        "Invalid Value: %s"
                    ) % line.contact_no)

            # One2many: Address Detail Contact Numbers
            for addr in rec.address_detail:
                if addr.business_phone and not phone_pattern.match(addr.business_phone):
                    raise ValidationError(_(
                        "Business Address Contact Number must be exactly 10 digits.\n"
                        "Invalid Value: %s"
                    ) % addr.business_phone)

    @api.constrains('email', 'director_email', 'directors_detail', 'address_detail')
    def _check_email_format(self):
        email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$')
        for rec in self:
            # Main Email
            if rec.email and not email_pattern.match(rec.email):
                raise ValidationError(_(
                    "Email must be valid (e.g., user@example.com).\nInvalid Value: %s"
                ) % rec.email)

            # Director Email
            if rec.director_email and not email_pattern.match(rec.director_email):
                raise ValidationError(_(
                    "Email must be valid (e.g., user@example.com).\nInvalid Value: %s"
                ) % rec.director_email)

            # One2many: Director Detail Emails
            for line in rec.directors_detail:
                if line.email and not email_pattern.match(line.email):
                    raise ValidationError(_(
                        "Email must be valid.\nInvalid Value: %s"
                    ) % line.email)

            # One2many: Address Detail Emails
            for addr in rec.address_detail:
                if addr.business_email and not email_pattern.match(addr.business_email):
                    raise ValidationError(_(
                        "Business Address Email must be valid.\nInvalid Value: %s"
                    ) % addr.business_email)

    @api.constrains('address_detail')
    def _check_pincode_format(self):
        pincode_pattern = re.compile(r'^\d{6}$')  # Indian pincode: exactly 6 digits
        for rec in self:
            for addr in rec.address_detail:
                if addr.business_pincode and not pincode_pattern.match(addr.business_pincode):
                    raise ValidationError(_(
                        "Invalid Pincode: '%s'. It must be exactly 6 digits (e.g., 400001)."
                    ) % addr.business_pincode)

    @api.constrains('pan_no')
    def _check_pan_card_no_format(self):
        pan_pattern = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
        for rec in self:
            if rec.pan_no and not pan_pattern.match(rec.pan_no.upper()):
                raise ValidationError(
                    _("PAN Card Number must be in the format: 5 letters, 4 digits, and 1 letter (e.g., ABCDE1234F).")
                )

    partner_id = fields.Many2one('res.partner', string='Contact', domain="[('id', '=', active_id)]")
    email = fields.Char("Email", required=True)
    point_of_contact = fields.Char("Point of Contact", required=True)
    user_id = fields.Many2one('res.users', string="Point of Contact to Vendor", default=lambda self: self.env.user, readonly=1)
    business_legal_name = fields.Char("Business Legal Name", required=True)
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
    # no_partner_director = fields.Many2one('number.partner.director', string="Number of Managing Partner / Directors")
    director_name = fields.Char(string="Name of the Owner / Director")
    director_phone = fields.Char(string="Contact Number")
    director_email = fields.Char(string="Email Address")
    aadhaar_card = fields.Binary(string="Aadhaar Card")
    pan_card = fields.Binary(string="PAN Card")

    gst_no = fields.Char(string="GST Number", required=True)
    udyam_number = fields.Char(string="Udyam Certificate Number", required=True)
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rel', 'wizard_id', 'attachment_id',
                                       string="GST Certificate(Latest)", required=True)

    udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rel', 'wizard_id', 'attachment_id',
                                      string="Udyam Documents", required=True)
    shop_act_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_act_documents_rel', 'wizard_id', 'attachment_id',
                                      string="Shop Act documents", required=True)

    gst_return_duration = fields.Selection([('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')],
                                           required=True, string="GST Return duration")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Photos", required=True,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Videos", required=True,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")
    ##### Partnership/PrivateCo./LLP
    no_partner_director = fields.Selection([('1', '1'),
                                            ('2', '2'),
                                            ('3', '3'),
                                            ('4', '4'),
                                            ('5', '5'),
                                            ('6', '6'),
                                            ('7', '7')], string="Number of Managing Partner / Directors")
    directors_detail = fields.One2many('director.detail', 'kyc_wizard_id', string="Directors Detail")
    bank_detail = fields.One2many('bank.detail', 'kyc_wizard_id', string="Bank Detail")
    address_detail = fields.One2many('address.detail', 'kyc_wizard_id', string="Address Detail")
    pan_no = fields.Char(string="PAN Number(Company)")
    pan_card_document = fields.Many2many('ir.attachment', 'pan_card_company_documents_rel', 'wizard_id', 'attachment_id',
                                      string="PAN Card Document(Company)")
    incorporation_certificate = fields.Many2many('ir.attachment', 'incorportaion_certificate_rel', 'wizard_id', 'attachment_id',
                                      string="Incorporation Certificate")
    google_location = fields.Char(string="Google Location of Shop", required=True)
    partner_llp = fields.Binary(string="Partnership Deed or LLP Deed")
    moa_aoa = fields.Many2many('ir.attachment', 'vendor_kyc_moa_aoa_rel', 'wizard_id', 'attachment_id',
                               string="MOA or AOA (for Pvt. Ltd. Company)")
    cin_no = fields.Char(string="CIN number")
    electricity_bill = fields.Many2many('ir.attachment', 'vendor_kyc_electricity_bill_rel', 'wizard_id',
                                        'attachment_id',
                                        string="Electricity bill", required=True)
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
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        res_id = self._context.get('active_id')
        res_model = self._context.get('active_model')
        if res_id and res_model:
            previous_record = self.env[res_model].browse(res_id)
            if previous_record:
                values['email'] = previous_record.email
                # values['street'] = previous_record.street
                # values['street2'] = previous_record.street2
                # values['city'] = previous_record.city
                # values['pincode'] = previous_record.zip
                # values['mobile'] = previous_record.mobile

            return values

    def action_vendor_kyc_done(self):
        self.ensure_one()

        if not self.partner_id:
            return

        def prepare_one2many(lines, fields_map, many2many_fields=None):
            result = []
            many2many_fields = many2many_fields or []
            for line in lines:
                item = {k: getattr(line, v) for k, v in fields_map.items()}
                for m2m_field in many2many_fields:
                    item[m2m_field] = [(6, 0, getattr(line, m2m_field).ids)]
                result.append((0, 0, item))
            return result

        # Prepare related data
        directors_data = prepare_one2many(
            self.directors_detail,
            fields_map={
                'name': 'name',
                'contact_no': 'contact_no',
                'email': 'email',
                'aadhaar_card': 'aadhaar_card',
                'pan_card': 'pan_card',
            }
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
            }
        )

        # Prepare main record values
        kyc_vals = {
            'partner_id': self.partner_id.id,
            'email': self.email,
            'point_of_contact': self.point_of_contact,
            'business_legal_name': self.business_legal_name,
            'business_trade_name': self.business_trade_name,
            'address_detail': address_data,
            'const_business': self.const_business,
            'other_business': self.other_business,
            'director_name': self.director_name,
            'director_phone': self.director_phone,
            'director_email': self.director_email,
            'aadhaar_card': self.aadhaar_card,
            'pan_card': self.pan_card,
            'gst_no': self.gst_no,
            'udyam_number': self.udyam_number,
            'no_partner_director': self.no_partner_director,
            'directors_detail': directors_data,
            'pan_no': self.pan_no,
            'google_location': self.google_location,
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
        attachment_fields = [
            self.gst_certificate,
            self.udyam_document,
            self.shop_act_document,
            self.shop_photos,
            self.electricity_bill,
            self.moa_aoa,
            self.pan_card_document,
            self.incorporation_certificate,
            self.shop_videos,
        ]
        all_attachments = sum((attachments for attachments in attachment_fields if attachments),
                              self.env['ir.attachment'])
        if all_attachments:
            all_attachments.write({
                'res_model': 'res.partner.kyc.approval',
                'res_id': kyc_record.id,
            })

        # Link bank cheque attachments separately
        for bank in kyc_record.bank_detail:
            if bank.bank_cheque_attachments:
                bank.bank_cheque_attachments.write({
                    'res_model': 'res.partner.kyc.approval',
                    'res_id': kyc_record.id,
                })

        # Update Partner
        self.partner_id.write({
            'email': self.email,
            'vat': self.gst_no,
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
    email = fields.Char(string="E-mail Address", required=True)
    aadhaar_card = fields.Binary(string="Aadhaar Card", required=True)
    pan_card = fields.Binary(string="PAN Card", required=True)

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

##### Principal Place of Business
class AddressDetail(models.TransientModel):
    _name = "address.detail"
    _description = "Address Detail"

    kyc_wizard_id = fields.Many2one('vendor.kyc.wizard', string="KYC Approval")
    business_street = fields.Char("Address", required=True)
    business_city = fields.Char("City", required=True)
    business_pincode = fields.Char("Pincode", required=True)
    business_phone = fields.Char("Contact Number", required=True)
    business_email = fields.Char("Email Address", required=True)
    business_state_id = fields.Many2one('res.country.state', string='Business State', domain="[('country_id', '=?', business_country_id)]")
    business_country_id = fields.Many2one('res.country', string='Business Country')

    @api.onchange('business_country_id')
    def _onchange_country_id(self):
        if self.business_country_id and self.business_country_id != self.business_state_id.country_id:
            self.business_state_id = False

    @api.onchange('business_state_id')
    def _onchange_state(self):
        if self.business_state_id.country_id and self.business_country_id != self.business_state_id.country_id:
            self.business_country_id = self.business_state_id.country_id

