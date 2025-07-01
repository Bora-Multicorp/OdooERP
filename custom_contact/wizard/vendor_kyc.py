# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class VendorKycWizard(models.TransientModel):
    _name = 'vendor.kyc.wizard'
    _description = 'Vendor KYC Wizard'

    partner_id = fields.Many2one('res.partner', string='Contact', domain="[('id', '=', active_id)]")
    email = fields.Char("Email", required=True)
    point_of_contact = fields.Char("Point of Contact", required=True)
    business_legal_name = fields.Char("Business Legal Name", required=True)
    business_trade_name = fields.Char("Business Trade Name", required=True)
    business_street = fields.Char("Address", required=True)
    business_city = fields.Char("City", required=True)
    business_pincode = fields.Char("Pincode", required=True)
    additional_street = fields.Char("Address")
    additional_city = fields.Char("City")
    additional_zip = fields.Char("Pincode")
    additional_phone = fields.Char("Contact Number", required=True)
    additional_email = fields.Char("Email Address")
    const_business = fields.Selection([('Sole Proprietor', 'Sole Proprietor'),
                                              ('Partnership', 'Partnership'),
                                              ('Pvt Ltd Co.', 'Pvt Ltd Co.'),
                                              ('LLP', 'LLP'),
                                              ('HUF(Karta)', 'HUF(Karta)'),
                                              ], string="Constitution of Business", required=True)
    # const_business = fields.Many2one('constitution.business', string="Constitution of Business", required=True)
    other_business = fields.Char("If Other, Specify?")
    # no_partner_director = fields.Many2one('number.partner.director', string="Number of Managing Partner / Directors")
    director_name = fields.Char(string="Name of the Owner / Director", required=True)
    director_phone = fields.Char(string="Contact Number", required=True)
    director_email = fields.Char(string="Email Address", required=True)
    aadhaar_card = fields.Binary(string="Aadhaar Card", required=True)
    pan_card = fields.Binary(string="PAN Card (Proprietor)", required=True)
    gst_no = fields.Char(string="GST Number", required=True)
    udyam_number = fields.Char(string="Udyam Certificate Number")
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rel', 'wizard_id', 'attachment_id',
                                       string="Company GST Certificate", required=True)

    udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rel', 'wizard_id', 'attachment_id',
                                      string="Shop Act documents / Udyam Documents", required=True)

    gst_return_duration = fields.Selection([('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')],
                                           required=True, string="GST Return duration")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Photos", required=True,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rel', 'wizard_id', 'attachment_id',
                                   string="Shop Videos", required=True,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    bank_name = fields.Char(string="Bank Name", required=True)
    account_no = fields.Char(string="Account Number", required=True)
    ifsc_code = fields.Char(string="IFSC Code", required=True)
    bank_address = fields.Char(string="Bank Address", required=True)
    bank_cheque_attachments = fields.Many2many('ir.attachment', 'vendor_kyc_bank_cheque_rel', 'wizard_id',
                                               'attachment_id', string="Cancelled Cheques", required=True)

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
                # values['state_id'] = previous_record.state_id.id
                # values['pincode'] = previous_record.zip
                # values['country_id'] = previous_record.country_id.id
                # values['mobile'] = previous_record.mobile

            return values

    def action_vendor_kyc_done(self):
        self.ensure_one()

        if not self.partner_id:
            return

        self.env['res.partner.kyc.approval'].create({
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

        return {'type': 'ir.actions.act_window_close'}
