# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ContactKYCApproval(models.Model):
    _name = 'res.partner.kyc.approval'
    _description = 'Contact KYC approvals'
    _rec_name = 'partner_id'

    def confirm_submit_form(self):
        if self.id:
            self.write({'state': 'pending'})

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
    state = fields.Selection([('draft', 'Draft'),
                              ('pending', 'Pending Approval'),
                              ('confirmed', 'Confirmed'),
                              ('rejected', 'Rejected'),
                              ('expired', 'Expired')], default='draft', required=True, string="Status")
    approval_users_ids = fields.One2many('approval.users', 'kyc_approval_id', 'Approval Authorities',
                                          help='Approval Authority Details')


class ApprovalUsers(models.Model):
    _name = "approval.users"
    _rec_name = 'kyc_approval_id'
    _description = "Approval Users"
    _order = "sequence"

    sequence = fields.Integer(string='Sequence')
    kyc_approval_id = fields.Many2one('res.partner.kyc.approval', string="KYC Approval")
    job_id = fields.Char(string="Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)
    state = fields.Selection([('approve', 'Approved'), ('reject', 'Rejected')], string="Action")
    remark = fields.Text('Remarks', tracking=True)
    action_date = fields.Datetime(string="Action Date")