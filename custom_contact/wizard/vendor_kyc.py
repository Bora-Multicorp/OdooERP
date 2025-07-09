# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class VendorKycWizard(models.TransientModel):
    _name = 'vendor.kyc.wizard'
    _description = 'Vendor KYC Wizard'

    @api.constrains('director_phone')
    def _check_phone_numbers(self):
        phone_pattern = re.compile(r'^\+?[0-9]{10,14}$')  # Accepts optional '+' and 7–15 digits
        for rec in self:
            for field_label, number in [('Director Contact Number', rec.director_phone)]:
                if number and not phone_pattern.match(number):
                    raise ValidationError(
                        f"{field_label} must be a valid phone number (e.g., +911234567890 or 1234567890).")

    @api.constrains('email', 'director_email')
    def _check_email_format(self):
        email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$')  # More flexible TLD length
        for rec in self:
            for label, email in [('Email', rec.email),
                                 ('Director Email', rec.director_email)]:
                if email and not email_pattern.match(email):
                    raise ValidationError(f"{label} must be a valid email address (e.g., user@example.com).")

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
    udyam_number = fields.Char(string="Udyam Certificate Number")
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rel', 'wizard_id', 'attachment_id',
                                       string="Company GST Certificate", required=True)

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
    bank_detail = fields.One2many('bank.detail', 'kyc_wizard_id', string="Banks Detail")
    address_detail = fields.One2many('address.detail', 'kyc_wizard_id', string="Address Detail")
    pan_no = fields.Char(string="PAN Number(Company)")
    pan_card_document = fields.Many2many('ir.attachment', 'pan_card_company_documents_rel', 'wizard_id', 'attachment_id',
                                      string="PAN Card Document(Company)")
    google_location = fields.Char(string="Google Location of Shop")
    partner_llp = fields.Binary(string="Partnership Deed or LLP Deed")
    moa_aoa = fields.Many2many('ir.attachment', 'vendor_kyc_moa_aoa_rel', 'wizard_id', 'attachment_id',
                               string="MOA or AOA (for Pvt. Ltd. Company)")
    cin_no = fields.Char(string="CIN number")
    electricity_bill = fields.Many2many('ir.attachment', 'vendor_kyc_electricity_bill_rel', 'wizard_id',
                                        'attachment_id',
                                        string="Electricity bill", required=True)
    #####

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

        # Prepare director detail lines
        directors_data = [
            (0, 0, {
                'name': director.name,
                'contact_no': director.contact_no,
                'email': director.email,
                'aadhaar_card': director.aadhaar_card,
                'pan_card': director.pan_card,
            }) for director in self.directors_detail
        ]
        # Prepare bank detail lines
        bank_data = [
            (0, 0, {
                'bank_name': bank.bank_name,
                'account_no': bank.account_no,
                'ifsc_code': bank.ifsc_code,
                'bank_address': bank.bank_address,
                'bank_cheque_attachments': [(6, 0, bank.bank_cheque_attachments.ids)],
            }) for bank in self.bank_detail
        ]
        # Prepare Address detail lines
        address_data = [
            (0, 0, {
                'business_street': address.business_street,
                'business_city': address.business_city,
                'business_pincode': address.business_pincode,
                'business_phone': address.business_phone,
                'business_email': address.business_email,
            }) for address in self.address_detail
        ]

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
            'gst_certificate': [(6, 0, self.gst_certificate.ids)],
            'udyam_document': [(6, 0, self.udyam_document.ids)],
            'gst_return_duration': self.gst_return_duration,
            'shop_photos': [(6, 0, self.shop_photos.ids)],
            'shop_videos': [(6, 0, self.shop_videos.ids)],
            'bank_detail': bank_data,
        }

        kyc_record = self.env['res.partner.kyc.approval'].create(kyc_vals)

        # Ensure uploaded attachments are linked correctly to kyc record
        all_attachments = (
                self.gst_certificate |
                self.udyam_document |
                self.shop_photos |
                self.shop_videos
        )
        if all_attachments:
            all_attachments.write({
                'res_model': 'res.partner.kyc.approval',
                'res_id': kyc_record.id
            })
        # Set res_model and res_id for bank cheque attachments
        for bank in kyc_record.bank_detail:
            if bank.bank_cheque_attachments:
                bank.bank_cheque_attachments.write({
                    'res_model': 'res.partner.kyc.approval',
                    'res_id': kyc_record.id,
                })

        # Update linked partner
        self.partner_id.write({
            'email': self.email,
            'is_kyc': True,
            'vat': self.gst_no,
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
    designation = fields.Char(string="Designation")
    name = fields.Char(string="Name")
    contact_no = fields.Char(string="Contact Number")
    email = fields.Char(string="E-mail Address")
    aadhaar_card = fields.Binary(string="Aadhaar Card")
    pan_card = fields.Binary(string="PAN Card")

##### Bank Details
class BankDetail(models.TransientModel):
    _name = "bank.detail"
    _rec_name = 'bank_name'
    _description = "Bank Detail"

    kyc_wizard_id = fields.Many2one('vendor.kyc.wizard', string="KYC Approval")
    bank_name = fields.Char(string="Bank Name", required=False)
    account_no = fields.Char(string="Account Number", required=False)
    ifsc_code = fields.Char(string="IFSC Code", required=False)
    bank_address = fields.Char(string="Bank Address", required=False)
    bank_cheque_attachments = fields.Many2many('ir.attachment', 'wizard_bank_detail_cheque_rel', 'kyc_wizard_id',
                                               'attachment_id', string="Cancelled Cheques", required=False)

##### Principal Place of Business
class AddressDetail(models.TransientModel):
    _name = "address.detail"
    _description = "Address Detail"

    kyc_wizard_id = fields.Many2one('vendor.kyc.wizard', string="KYC Approval")
    business_street = fields.Char("Address", required=False)
    business_city = fields.Char("City", required=False)
    business_pincode = fields.Char("Pincode", required=False)
    business_phone = fields.Char("Contact Number", required=False)
    business_email = fields.Char("Email Address")
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

