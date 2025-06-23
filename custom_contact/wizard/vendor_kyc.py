# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class VendorKycWizard(models.TransientModel):
    _name = 'vendor.kyc.wizard'
    _description = 'Vendor KYC Wizard'

    partner_id = fields.Many2one('res.partner', string='Contact', domain="[('id', '=', active_id)]")
    email = fields.Char("Email", required=1)
    point_of_contact = fields.Char("Point of Contact", required=1)
    business_name = fields.Char("Business Legal Name", required=1)
    trade_name = fields.Char("Business Trade Name", required=1)
    street = fields.Char("Address", required=1)
    street2 = fields.Char("Address")
    city = fields.Char("City", required=1)
    pincode = fields.Char("Pincode", required=1)
    add_address = fields.Char("Address")
    add_city = fields.Char("City")
    add_pincode = fields.Char("Pincode")
    contact_no = fields.Char("Contact Number")
    email_add = fields.Char("Email Address")
    const_business = fields.Many2one('constitution.business', string="Constitution of Business")
    other_business = fields.Char()
    no_partner_director = fields.Many2one('number.partner.director', string="Number of Managing Partner / Directors")
    name_owner = fields.Char(string="Name of the Owner / Director", required=1)
    bus_contact_number = fields.Char(string="Contact Number", required=1)
    email_address = fields.Char(string="Email Address", required=1)
    aadhaar_card = fields.Binary(string="Aadhaar Card", required=1)
    pan_card = fields.Binary(string="PAN Card (Proprietor)", required=1)
    gst_no = fields.Char(string="GST Number", required=1)
    udyam_cert_no = fields.Char(string="Udyam Certificate Number")
    gst_cert = fields.Many2many('ir.attachment',
        'vendor_kyc_gst_cert_rel',
        'wizard_id',
        'attachment_id',
        string="Company GST Certificate",
        required=True
    )

    shop_documents = fields.Many2many(
        'ir.attachment',
        'vendor_kyc_shop_documents_rel',
        'wizard_id',
        'attachment_id',
        string="Shop Act documents / Udyam Documents",
        required=True
    )

    gst_return_duration = fields.Selection(
        [('monthly', 'Monthly'), ('quarterly', 'Quarterly')],
        required=True,
        string="GST Return duration"
    )

    shop_photos = fields.Many2many('ir.attachment',
        'vendor_kyc_shop_photos_rel',
        'wizard_id',
        'attachment_id',
        string="Shop Photos",
        required=True,
        help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number."
    )

    shop_videos = fields.Many2many('ir.attachment',
        'vendor_kyc_shop_videos_rel',
        'wizard_id',
        'attachment_id',
        string="Shop Videos",
        required=True,
        help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number."
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
                values['street'] = previous_record.street
                values['street2'] = previous_record.street2
                values['city'] = previous_record.city
                values['state_id'] = previous_record.state_id.id
                values['pincode'] = previous_record.zip
                values['country_id'] = previous_record.country_id.id
                values['mobile'] = previous_record.mobile

            return values

    def action_vendor_kyc_done(self):
        self.ensure_one()
        partner = self.partner_id

        if not partner:
            return

        # Basic field mappings (many fields share the same name)
        values = {
            'vendor_customer_email': self.email,
            'point_of_contact': self.point_of_contact,
            'business_name': self.business_name,
            'trade_name': self.trade_name,
            'city': self.city,
            'pincode': self.pincode,
            'add_address': self.add_address,
            'add_city': self.add_city,
            'add_pincode': self.add_pincode,
            'contact_no': self.contact_no,
            'email_add': self.email_add,
            'const_business': self.const_business.id,
            'no_partner_director': self.no_partner_director.id,
            'name_owner': self.name_owner,
            'bus_contact_number': self.bus_contact_number,
            'email_address': self.email_address,
            'aadhaar_card': self.aadhaar_card,
            'pan_card': self.pan_card,
            'gst_no': self.gst_no,
            'udyam_cert_no': self.udyam_cert_no,
            'gst_return_duration': self.gst_return_duration,

        }

        # Write basic fields
        partner.write(values)

        # Write many2many fields separately
        partner.gst_cert = [(6, 0, self.gst_cert.ids)]
        partner.shop_documents = [(6, 0, self.shop_documents.ids)]
        partner.shop_photos = [(6, 0, self.shop_photos.ids)]
        partner.shop_videos = [(6, 0, self.shop_videos.ids)]

        # Write customer/vendor option
        # if self.vendor_customer == 'vendor':
        #     partner.write({'supplier_rank': 1})
        # else:
        #     partner.write({'customer_rank': 1})

        return {'type': 'ir.actions.act_window_close'}

