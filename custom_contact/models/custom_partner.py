# -*- coding: utf-8 -*-
from email.policy import default

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

    custom_type = fields.Many2one('res.partner.location.type', string="Type", tracking=True,
                                  help='Contact Location Type', copy=False)
    custom_address_type = fields.Many2one('res.partner.address.type', string="Address Type", tracking=True,
                                          help='Contact Address Type', copy=False)
    tally_name = fields.Char(string="Tally Name", tracking=True)
    purpose = fields.Char(string="Purpose", tracking=True)
    # Customer/Vendor KYC Details
    is_vendor = fields.Boolean(string="Is Vendor?")
    is_customer = fields.Boolean(string="Is Customer?")
    is_kyc = fields.Boolean(string="Is KYC?")
    is_expiry = fields.Boolean(string="Is Expiry?")

    kyc_details = fields.One2many("res.partner.kyc.detail", "partner_id", string="KYC Details", tracking=True)


class ContactKYCDetail(models.Model):
    _name = 'res.partner.kyc.detail'
    _description = 'Contact KYC Details'

    partner_id = fields.Many2one('res.partner', string="Contact")
    email = fields.Char("Email")
    point_of_contact = fields.Char("Point of Contact / Purchase Manager (Bora Multicorp)")
    business_legal_name = fields.Char("Business Legal Name")
    business_trade_name = fields.Char("Business Trade Name")
    business_street = fields.Char("Address")
    business_city = fields.Char("City")
    business_pincode = fields.Char("Pincode")
    additional_street = fields.Char("Address")
    additional_city = fields.Char("City")
    additional_zip = fields.Char("Pincode")
    additional_phone = fields.Char("Contact Number")
    additional_email = fields.Char("Email Address")
    const_business = fields.Selection([('Sole Proprietor', 'Sole Proprietor'),
                                       ('Partnership', 'Partnership'),
                                       ('Pvt Ltd Co.', 'Pvt Ltd Co.'),
                                       ('LLP', 'LLP'),
                                       ('HUF(Karta)', 'HUF(Karta)'),
                                       ], string="Constitution of Business", required=False)
    # const_business = fields.Many2one('constitution.business', string="Constitution of Business", required=True)
    other_business = fields.Char("If Other, Specify?")
    # no_partner_director = fields.Many2one('number.partner.director', string="Number of Managing Partner / Directors")
    director_name = fields.Char(string="Name of the Owner / Director")
    director_phone = fields.Char(string="Contact Number")
    director_email = fields.Char(string="Email Address")
    aadhaar_card = fields.Binary(string="Aadhaar Card")
    pan_card = fields.Binary(string="PAN Card (Proprietor)")
    gst_no = fields.Char(string="GST Number")
    udyam_number = fields.Char(string="Udyam Certificate Number")
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rel1', 'wizard_id', 'attachment_id',
                                       string="Company GST Certificate", required=True)

    udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rel1', 'wizard_id', 'attachment_id',
                                      string="Shop Act documents / Udyam Documents", required=True)

    gst_return_duration = fields.Selection([('Monthly', 'Monthly'), ('Quarterly', 'Quarterly')],
                                           required=True, string="GST Return duration")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rel1', 'wizard_id', 'attachment_id',
                                   string="Shop Photos", required=True,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rel1', 'wizard_id', 'attachment_id',
                                   string="Shop Videos", required=True,
                                   help="Short Video / Walkway from outdoor / indoor. Must include - signage Board with GST Number.")

    bank_name = fields.Char(string="Bank Name", required=True)
    account_no = fields.Char(string="Account Number", required=True)
    ifsc_code = fields.Char(string="IFSC Code", required=True)
    bank_address = fields.Char(string="Bank Address", required=True)
    bank_cheque_attachments = fields.Many2many('ir.attachment', 'vendor_kyc_bank_cheque_rel1', 'wizard_id',
                                               'attachment_id', string="Cancelled Cheques")

    deadline = fields.Date('Deadline Date')
    state = fields.Selection([('draft', 'Draft'), ('running', 'Running'), ('expired', 'Expired')], default='draft',
                             required=True, string="Status")
