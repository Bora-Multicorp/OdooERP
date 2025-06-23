# -*- coding: utf-8 -*-
from odoo import api, fields, models

class CustomContact(models.Model):
    _inherit = 'res.partner'

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

    custom_type = fields.Many2one('res.partner.location.type', string="Type", tracking=True, help='Contact Location Type', copy=False)
    custom_address_type = fields.Many2one('res.partner.address.type', string="Address Type", tracking=True, help='Contact Address Type', copy=False)
    tally_name = fields.Char(string="Tally Name", tracking=True)
    purpose = fields.Char(string="Purpose", tracking=True)
    #Customer/Vendor KYC Details
    is_vendor = fields.Boolean(string="Vendor")
    is_customer = fields.Boolean(string="Customer")
    vendor_customer_email = fields.Char("Email", required=1)
    point_of_contact = fields.Char("Point of Contact / Purchase Manager (Bora Multicorp)", required=1)
    business_name = fields.Char("Business Legal Name", required=1)
    trade_name = fields.Char("Business Trade Name", required=1)
    address1 = fields.Char("Address", required=1)
    city1 = fields.Char("City", required=1)
    pincode1 = fields.Char("Pincode", required=1)
    add_address = fields.Char("Address")
    add_city = fields.Char("City")
    add_pincode = fields.Char("Pincode")
    contact_no = fields.Char("Contact Number")
    email_add = fields.Char("Email Address")
    const_business = fields.Many2one('constitution.business', string="Constitution of Business")
    no_partner_director = fields.Many2one('number.partner.director', string="Number of Managing Partner / Directors")
    name_owner = fields.Char(string="Name of the Owner / Director", required=1)
    bus_contact_number = fields.Char(string="Contact Number", required=1)
    email_address = fields.Char(string="Email Address", required=1)
    aadhaar_card = fields.Binary(string="Aadhaar Card", required=1)
    pan_card = fields.Binary(string="PAN Card (Proprietor)", required=1)
    gst_no = fields.Char(string="GST Number", required=1)
    udyam_cert_no = fields.Char(string="Udyam Certificate Number")
    gst_cert = fields.Many2many('ir.attachment',
                                'vendor_kyc_gst_cert_rel1',
                                'wizard_id',
                                'attachment_id',
                                string="Company GST Certificate",
                                required=True
                                )

    shop_documents = fields.Many2many(
        'ir.attachment',
        'vendor_kyc_shop_documents_rel1',
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
                                   'vendor_kyc_shop_photos_rel1',
                                   'wizard_id',
                                   'attachment_id',
                                   string="Shop Photos",
                                   required=True,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number."
                                   )

    shop_videos = fields.Many2many('ir.attachment',
                                   'vendor_kyc_shop_videos_rel1',
                                   'wizard_id',
                                   'attachment_id',
                                   string="Shop Videos",
                                   required=True,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number."
                                   )
