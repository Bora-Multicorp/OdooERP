# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import re


class VendorKycWizard(models.TransientModel):
    _name = 'vendor.kyc.wizard'
    _description = 'Vendor KYC Wizard'

    @api.constrains('additional_phone', 'director_phone')
    def _check_phone_numbers(self):
        phone_pattern = re.compile(r'^\+?[0-9]{10,14}$')  # Accepts optional '+' and 7–15 digits
        for rec in self:
            for field_label, number in [('Additional Contact Number', rec.additional_phone),
                                        ('Director Contact Number', rec.director_phone)]:
                if number and not phone_pattern.match(number):
                    raise ValidationError(
                        f"{field_label} must be a valid phone number (e.g., +911234567890 or 1234567890).")

    @api.constrains('email', 'additional_email', 'director_email')
    def _check_email_format(self):
        email_pattern = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$')  # More flexible TLD length
        for rec in self:
            for label, email in [('Email', rec.email), ('Additional Email', rec.additional_email),
                                 ('Director Email', rec.director_email)]:
                if email and not email_pattern.match(email):
                    raise ValidationError(f"{label} must be a valid email address (e.g., user@example.com).")

    partner_id = fields.Many2one('res.partner', string='Contact', domain="[('id', '=', active_id)]")
    email = fields.Char("Email", required=True)
    point_of_contact = fields.Char("Point of Contact", required=False)
    business_legal_name = fields.Char("Business Legal Name", required=False)
    business_trade_name = fields.Char("Business Trade Name", required=False)
    business_street = fields.Char("Address", required=False)
    business_city = fields.Char("City", required=False)
    business_pincode = fields.Char("Pincode", required=False)
    additional_street = fields.Char("Address")
    additional_city = fields.Char("City")
    additional_zip = fields.Char("Pincode")
    additional_phone = fields.Char("Contact Number", required=False)
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
    director_name = fields.Char(string="Name of the Owner / Director", required=False)
    director_phone = fields.Char(string="Contact Number", required=False)
    director_email = fields.Char(string="Email Address", required=False)
    aadhaar_card = fields.Binary(string="Aadhaar Card", required=False)
    pan_card = fields.Binary(string="PAN Card (Proprietor)", required=False)
    gst_no = fields.Char(string="GST Number", required=False)
    udyam_number = fields.Char(string="Udyam Certificate Number")
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rel', 'wizard_id', 'attachment_id',
                                       string="Company GST Certificate", required=False)

    udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rel', 'wizard_id', 'attachment_id',
                                      string="Shop Act documents / Udyam Documents", required=False)

    gst_return_duration = fields.Selection([('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')],
                                           required=False, string="GST Return duration")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Photos", required=False,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Videos", required=False,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    bank_name = fields.Char(string="Bank Name", required=False)
    account_no = fields.Char(string="Account Number", required=False)
    ifsc_code = fields.Char(string="IFSC Code", required=False)
    bank_address = fields.Char(string="Bank Address", required=False)
    bank_cheque_attachments = fields.Many2many('ir.attachment', 'vendor_kyc_bank_cheque_rel', 'wizard_id',
                                               'attachment_id', string="Cancelled Cheques", required=False)

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

        kyc_record = self.env['res.partner.kyc.approval'].create({
            'partner_id': self.partner_id.id,
            'email': self.email,
            'point_of_contact': self.point_of_contact,
            'business_legal_name': self.business_legal_name,
            'business_trade_name': self.business_trade_name,
            'business_street': self.business_street,
            'business_city': self.business_city,
            'business_pincode': self.business_pincode,
            'additional_street': self.additional_street,
            'additional_city': self.additional_city,
            'additional_zip': self.additional_zip,
            'additional_phone': self.additional_phone,
            'additional_email': self.additional_email,
            'const_business': self.const_business,
            'other_business': self.other_business,
            'director_name': self.director_name,
            'director_phone': self.director_phone,
            'director_email': self.director_email,
            'aadhaar_card': self.aadhaar_card,
            'pan_card': self.pan_card,
            'gst_no': self.gst_no,
            'udyam_number': self.udyam_number,
            'gst_certificate': [(6, 0, self.gst_certificate.ids)],
            'udyam_document': [(6, 0, self.udyam_document.ids)],
            'gst_return_duration': self.gst_return_duration,
            'shop_photos': [(6, 0, self.shop_photos.ids)],
            'shop_videos': [(6, 0, self.shop_videos.ids)],
            'bank_name': self.bank_name,
            'account_no': self.account_no,
            'ifsc_code': self.ifsc_code,
            'bank_address': self.bank_address,
            'bank_cheque_attachments': [(6, 0, self.bank_cheque_attachments.ids)],
        })
        for attach in kyc_record:
            if attach.gst_certificate:
                attach.gst_certificate.write({'res_model': 'res.partner.kyc.approval', 'res_id': attach.id})
            if attach.udyam_document:
                attach.udyam_document.write({'res_model': 'res.partner.kyc.approval', 'res_id': attach.id})
            if attach.shop_photos:
                attach.shop_photos.write({'res_model': 'res.partner.kyc.approval', 'res_id': attach.id})
            if attach.shop_videos:
                attach.shop_videos.write({'res_model': 'res.partner.kyc.approval', 'res_id': attach.id})
            if attach.bank_cheque_attachments:
                attach.bank_cheque_attachments.write({'res_model': 'res.partner.kyc.approval', 'res_id': attach.id})


        self.partner_id.write({'email': self.email, 'is_kyc': True,
                               'vat': self.gst_no,
                               'street': self.business_street,
                               'city': self.business_city,
                               'zip': self.business_pincode
                               })

        return {'type': 'ir.actions.act_window_close'}
