# -*- coding: utf-8 -*-
import logging

from datetime import date

_logger = logging.getLogger(__name__)
import datetime
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ContactKYCApproval(models.Model):
    """
    Vendor KYC Master Record.
    Stores:
        - Company details
        - Uploaded documents
        - Director details
        - Bank details
        - Address details
        - Multi-level approval workflow
    """
    _name = 'res.partner.kyc.approval'
    _description = 'Vendor KYC approval'
    _rec_name = 'partner_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    # -------------------------------------------------------------------------
    # CREATE OVERRIDE → ensure attachments link to this record
    # -------------------------------------------------------------------------

    _sql_constraints = [
        ('unique_udyam_number', 'unique(udyam_number)',
         'The Udyam Certificate Number must be unique! This number is already registered.')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to:
        - Validate no duplicate KYC records (unless explicitly Re-KYC)
        - Create KYC record
        - Link attachments to `res.partner.kyc.approval`
        """
        # Check for duplicate KYC records before creating
        for vals in vals_list:
            partner_id = vals.get('partner_id')
            if partner_id:
                # Check if partner already has a KYC record
                existing_kyc = self.search([
                    ('partner_id', '=', partner_id)
                ], limit=1)
                
                # Only allow creation if explicitly marked as Re-KYC update (via context)
                # or if no existing KYC record exists
                is_rekyc_update = self._context.get('is_rekyc_update', False)
                if existing_kyc and not is_rekyc_update:
                    # Check if partner's is_kyc flag is False (indicating Re-KYC scenario)
                    partner = self.env['res.partner'].browse(partner_id)
                    if partner.is_kyc:
                        # Partner already has active KYC - this should be an update, not create
                        raise ValidationError(_(
                            "A KYC record already exists for this partner. "
                            "Please use Re-KYC to update the existing record instead of creating a new one."
                        ))
        
        res_list = super().create(vals_list)

        attachment_fields = [
            'gst_certificate', 'udyam_document', 'shop_act_document',
            'shop_photos', 'shop_videos', 'pan_card_document',
            'incorporation_certificate', 'moa_aoa', 'electricity_bill',
            'company_reg_document', 'authorized_person_id_document',
        ]

        for record in res_list:
            for field in attachment_fields:
                attachments = record[field]
                attachments.write({'res_model': self._name, 'res_id': record.id})

        return res_list


    # -------------------------------------------------------------------------
    # Compute existing users (approvers assigned)
    # -------------------------------------------------------------------------
    @api.depends('approval_users_ids.user_id')
    def _compute_existing_users(self):
        """
        Create m2m list of all user_ids present in approval lines.
        Used in notifications.
        """
        for record in self:
            record.existing_user_ids = [(6, 0, record.approval_users_ids.mapped('user_id').ids)]

    @api.depends('approval_users_ids.user_id', 'approval_users_ids.state', 'approval_users_ids.is_active')
    @api.depends_context('uid')
    def _compute_has_pending_approval(self):
        """Check if current user has a pending approval request (sequential - only current approver)"""
        current_user = self.env.user
        for record in self:
            # Only consider active approval lines with no decision yet (pending)
            pending_approvers = sorted(
                record.approval_users_ids.filtered(lambda l: l.is_active and not l.state),
                key=lambda l: l.sequence
            )
            # Only show approval button if current user is the first pending approver
            if pending_approvers and pending_approvers[0].user_id.id == current_user.id:
                record.has_pending_approval = True
            else:
                record.has_pending_approval = False

    @api.depends('partner_id.user_ids')
    @api.depends_context('uid')
    def _compute_is_partner_user(self):
        """Check if current user is the partner's user"""
        current_user = self.env.user
        for record in self:
            record.is_partner_user = bool(record.partner_id and current_user in record.partner_id.user_ids)

    @api.depends_context('uid')
    def _compute_is_admin_user(self):
        """Check if current user is an admin (has base.group_system)"""
        current_user = self.env.user
        is_admin = current_user.has_group('base.group_system')
        for record in self:
            record.is_admin_user = is_admin

    @api.depends('create_uid')
    @api.depends_context('uid')
    def _compute_is_form_owner(self):
        """Check if current user is the creator/owner of the form"""
        current_user = self.env.user
        for record in self:
            record.is_form_owner = bool(record.create_uid and record.create_uid == current_user)

    @api.depends('poc_user', 'rekyc_state')
    @api.depends_context('uid')
    def _compute_can_rekyc_approve(self):
        current_user = self.env.user
        for record in self:
            record.can_rekyc_approve = bool(
                record.rekyc_state == 'pending'
                and record.poc_user
                and record.poc_user == current_user
            )


    # -------------------------------------------------------------------------
    # KYC Fields
    # -------------------------------------------------------------------------

    partner_id = fields.Many2one('res.partner', string="Contact", tracking=True)
    email = fields.Char("Email", tracking=True)
    point_of_contact = fields.Char("Vendor POC", tracking=True)
    poc_user = fields.Many2one('res.users', string="Bora Purchase Manager", tracking=True)
    business_legal_name = fields.Char("Business Legal Name", tracking=True)
    is_same_trade_name = fields.Boolean("If Trade Name is same as Legal Name", tracking=True)
    business_trade_name = fields.Char("Business Trade Name", tracking=True)

    # Address Fields
    business_street = fields.Char("Address", tracking=True)
    business_city = fields.Char("City", tracking=True)
    business_pincode = fields.Char("Pincode", tracking=True)
    additional_street = fields.Char("Address", tracking=True)
    additional_city = fields.Char("City", tracking=True)
    additional_zip = fields.Char("Pincode", tracking=True)
    additional_phone = fields.Char("Contact Number", tracking=True)
    additional_email = fields.Char("Email Address", tracking=True)

    const_business = fields.Selection([
        ('Sole Proprietor', 'Sole Proprietor'),
        ('Partnership', 'Partnership'),
        ('Pvt Ltd Co.', 'Pvt Ltd Co.'),
        ('LLP', 'LLP'),
        ('HUF(Karta)', 'HUF(Karta)'),
        ('Other', 'Other'),
    ], string="Constitution of Business")

    other_business = fields.Char("If Other, Specify?", tracking=True)

    aadhaar_pan_link = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                        string='Aadhar and PAN card linking?')

    gst_no = fields.Char("GST Number")
    license_registered = fields.Char("Any licenses registered")
    udyam_number = fields.Char("Udyam Certificate Number")

    # Document Upload Fields (Many2many attachments)
    gst_certificate = fields.Many2many('ir.attachment', 'vendor_kyc_gst_cert_rels',
                                       'partner_id', 'attachment_id', string="GST Certificate")

    shop_act_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_act_documents_rels',
                                         'partner_id', 'attachment_id', string="Shop Act documents")

    pan_card_document = fields.Many2many('ir.attachment', 'pan_card_company_documents_rels',
                                         'partner_id', 'attachment_id', string="PAN Card Document (Company)")

    udyam_document = fields.Many2many('ir.attachment', 'vendor_kyc_shop_documents_rels',
                                      'partner_id', 'attachment_id', string="Udyam Documents")

    gst_return_duration = fields.Selection([
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly')
    ], string="Filing Frequency")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rels',
                                   'partner_id', 'attachment_id', string="Shop Photos")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rels',
                                   'partner_id', 'attachment_id', string="Shop Videos")

    no_partner_director = fields.Selection([(str(x), str(x)) for x in range(1, 8)],
                                           string="No. of Managing Partner / Directors")

    directors_detail = fields.One2many('director.details', 'kyc_approval_id', string="KYC Details", tracking=True)
    pan_no = fields.Char("PAN Number")
    comp_google_loc = fields.Char("GPS Location of Shop")
    partner_llp_filename = fields.Char()
    partner_llp = fields.Binary("Partnership/LLP Deed")

    moa_aoa = fields.Many2many('ir.attachment', 'vendor_kyc_moa_aoa_rels',
                               'partner_id', 'attachment_id', string="MOA/AOA")

    cin_no = fields.Char("CIN number")
    electricity_bill = fields.Many2many('ir.attachment', 'vendor_kyc_electricity_bill_rels',
                                        'partner_id', 'attachment_id', string="Electricity bill")

    incorporation_certificate = fields.Many2many('ir.attachment', 'incorportaion_certificate_rels',
                                                 'partner_id', 'attachment_id', string="Incorporation Certificate")

    # ── Overseas flag (drives view visibility on this form) ─────────────────────
    is_overseas = fields.Boolean(
        string='Is Overseas',
        related='partner_id.is_overseas',
        store=False,
        help="Mirrors the partner's Overseas Customer flag. Controls which document "
             "sections are visible on this KYC record.",
    )

    # ── Overseas KYC Documents ──────────────────────────────────────────────────
    company_reg_document = fields.Many2many(
        'ir.attachment', 'kyc_approval_company_reg_rel', 'kyc_id', 'attachment_id',
        string="Company Registration / Trade License",
        help="Trade License (UAE/Dubai), Business Registration Certificate (Hong Kong), "
             "Certificate of Incorporation, or equivalent country-specific document "
             "proving the legal existence of the company.",
    )
    authorized_person_id_document = fields.Many2many(
        'ir.attachment', 'kyc_approval_auth_person_id_rel', 'kyc_id', 'attachment_id',
        string="Authorized Person Identity Proof",
        help="Emirates ID / Passport (UAE), HKID / Passport (Hong Kong), "
             "or equivalent government-issued photo ID of the authorized signatory / manager.",
    )

    # ── Overseas document expiry dates ─────────────────────────────────────────
    company_reg_doc_expiry = fields.Date(
        string="Trade License / Company Reg. Expiry Date",
        tracking=True,
        help="Expiry date of the Company Registration or Trade License document.",
    )
    authorized_person_id_expiry = fields.Date(
        string="Authorized Person ID Expiry Date",
        tracking=True,
        help="Expiry date of the Authorized Person's identity document (Emirates ID / HKID / Passport).",
    )

    bank_detail = fields.One2many('bank.details', 'kyc_approval_id', string="Banks Detail")
    address_detail = fields.One2many('address.details', 'kyc_approval_id', string="Address Detail")

    deadline = fields.Date('Deadline Date', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    approval_users_ids = fields.One2many(
        'approval.users', 'kyc_approval_id', string="Approval Authorities"
    )

    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_users', store=True)
    
    # Computed field to check if current user has pending approval
    has_pending_approval = fields.Boolean(
        compute='_compute_has_pending_approval',
        string='Has Pending Approval',
        help='True if current user has a pending approval request'
    )
    
    # Computed field to check if current user is the partner's user
    is_partner_user = fields.Boolean(
        compute='_compute_is_partner_user',
        string='Is Partner User',
    )
    
    # Computed field to check if current user is an admin
    is_admin_user = fields.Boolean(
        compute='_compute_is_admin_user',
        string='Is Admin User',
    )
    
    # Computed field to check if current user is the form creator/owner
    is_form_owner = fields.Boolean(
        compute='_compute_is_form_owner',
        string='Is Form Owner',
    )

    is_approved = fields.Boolean(related='partner_id.is_approved', store=True)

    approval_date = fields.Datetime("Approval Date", tracking=True)
    is_rejected = fields.Boolean(tracking=True)
    rejection_date = fields.Datetime("Rejection Date", tracking=True)
    rejection_reason = fields.Text('Rejection Reason', tracking=True)
    kyc_approval_creator = fields.Many2one('res.users',string='KYC Approval Creator')

    can_set_draft = fields.Boolean(
        compute="_compute_can_set_draft", string="Can Set Draft"
    )
    rekyc_state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True, copy=False)
    rekyc_pending_payload = fields.Json(copy=False)
    rekyc_requested_by = fields.Many2one('res.users', string='Re-KYC Requested By', tracking=True, copy=False)
    rekyc_requested_on = fields.Datetime(string='Re-KYC Requested On', tracking=True, copy=False)
    rekyc_approved_by = fields.Many2one('res.users', string='Re-KYC Approved By', tracking=True, copy=False)
    rekyc_approved_on = fields.Datetime(string='Re-KYC Approved On', tracking=True, copy=False)
    rekyc_rejected_by = fields.Many2one('res.users', string='Re-KYC Rejected By', tracking=True, copy=False)
    rekyc_rejected_on = fields.Datetime(string='Re-KYC Rejected On', tracking=True, copy=False)
    rekyc_rejection_reason = fields.Text(string='Re-KYC Rejection Reason', tracking=True, copy=False)
    can_rekyc_approve = fields.Boolean(compute='_compute_can_rekyc_approve')

    # -------------------------------------------------------------------------
    # Compute draft button visibility
    # -------------------------------------------------------------------------
    def _compute_can_set_draft(self):
        """
        Only creator or non-approvers can set back to draft.
        Approvers should not edit their own approval workflow.
        """
        for rec in self:
            if rec.kyc_approval_creator:
                rec.can_set_draft = rec.kyc_approval_creator == self.env.user
            else:
                rec.can_set_draft = False

    # -------------------------------------------------------------------------
    # Approval assignment logic
    # -------------------------------------------------------------------------
    def add_user(self, approvers):
        """
        Add approval users to workflow and move state → pending.
        Creates activities for ALL approvers simultaneously (parallel approval).
        """
        vals = [(0, 0, {
            'sequence': idx + 1,
            'user_id': approval.user_id.id
        }) for idx, approval in enumerate(approvers)]

        self.write({'approval_users_ids': vals, 'state': 'pending','kyc_approval_creator': self.env.user.id})
        
        # Create activity only for first approver (sequential approval)
        self._schedule_sequential_approval_activities()

    # -------------------------------------------------------------------------
    # Submit KYC Approval
    # -------------------------------------------------------------------------
    def confirm_submit_form(self):
        """
        Submit KYC for approval - accessible only to admin or form owner.
        Security check: Only admin users or the form creator can submit.
        """
        self.ensure_one()
        current_user = self.env.user
        
        # Security check: Only admin or form owner can submit
        is_admin = current_user.has_group('base.group_system')
        is_owner = self.create_uid and self.create_uid == current_user
        
        if not (is_admin or is_owner):
            raise ValidationError(_("Access Denied: Only administrators or the form creator can submit for approval."))
        
        # Check if approval config exists
        config = self.env['vendor.approval.config'].get_config()
        if not config:
            raise ValidationError(_("Please configure Vendor Approval Settings before Submit Request"))
        
        # Check approvers based on approval mode
        if config.ks_approval_mode == 'two_way':
            if not config.ks_approver_1_ids or not config.ks_approver_2_ids:
                raise ValidationError(_("Please configure both Approver 1 and Approver 2 in Vendor Approval Settings before Submit Request"))
        else:
            if not config.ks_approver_1_ids:
                raise ValidationError(_("Please configure Approver 1 in Vendor Approval Settings before Submit Request"))

        # Return action without sudo() to maintain proper access control
        return {
            'name': _('Select Approval Users'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.kyc.approval.user.picker.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_kyc_id': self.id,
            },
        }


    # -------------------------------------------------------------------------
    # Update Approvals (safe: cleanup only on wizard OK, never on Cancel)
    # -------------------------------------------------------------------------

    def _ks_cancel_pending_kyc_activities(self, mark_done=False, feedback=None):
        """Cancel pending KYC approval activities on this record.

        Scoped by: res_model + res_id + user_ids of current approval_users_ids
        + summary keyword — so only KYC-approval activities are touched.

        :param mark_done: True  → action_feedback (leaves chatter entry)
                          False → unlink (silent, used for 'Update' resets)
        """
        self.ensure_one()
        approver_user_ids = self.approval_users_ids.mapped('user_id').ids
        domain = [
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('active', '=', True),
            ('summary', 'ilike', 'KYC Approval for'),
        ]
        if approver_user_ids:
            domain.append(('user_id', 'in', approver_user_ids))

        activities = self.env['mail.activity'].search(domain)
        if not activities:
            return True

        if mark_done:
            activities.action_feedback(feedback=feedback or '')
        else:
            activities.sudo().unlink()
        return True

    def action_update_approvals(self):
        """Requester/admin updates KYC approvers while KYC is in 'pending' state.

        Only opens the wizard with ks_is_update=True — ALL cleanup (cancel activities,
        reset approval_users_ids, reset state) happens inside the wizard's
        add_users_for_approval ONLY when the user clicks OK.
        Clicking the wizard Cancel button leaves everything untouched.
        """
        self.ensure_one()
        if self.state != 'pending':
            raise ValidationError(_("Update Approvals is only available while the KYC is in 'Pending' state."))

        current_user = self.env.user
        is_admin = current_user.has_group('base.group_system')
        is_owner = self.kyc_approval_creator and self.kyc_approval_creator == current_user
        if not (is_admin or is_owner):
            raise ValidationError(_("Only the original submitter or an administrator can update the approval request."))

        return {
            'name': _('Update Approval Users'),
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.kyc.approval.user.picker.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_kyc_id': self.id,
                'ks_is_update': True,
                'default_ks_is_update_mode': True,
                'default_approver1_user': self.approval_users_ids.filtered(lambda l: l.sequence == 1)[:1].user_id.id or False,
                'default_approver2_user': self.approval_users_ids.filtered(lambda l: l.sequence == 2)[:1].user_id.id or False,
            },
        }

    # -------------------------------------------------------------------------
    # Suspend Approval Process
    # -------------------------------------------------------------------------
    def action_suspend(self):
        """Return confirmation wizard"""
        return self.env.ref(
            "ks_contact.approve_suspend_vendor_confirm_wizard_action"
        ).sudo().read()[0]

    def suspend_approval_process(self, remark):
        """
        Suspend approval → all pending approvals are marked suspended.
        Notify:
            - creator
            - current user
        """

        self.message_post(
            body=f"Approval Suspended by {self.env.user.partner_id}. Reason: {remark}",
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        for kyc in self:
            pending = kyc.approval_users_ids.filtered(lambda u: not u.state)

            pending.write({
                'state': 'suspended',
                'remark': f"By {self.env.user.name} - {remark or ''}",
                'action_date': fields.Datetime.now(),
            })

            # Remove all activity tasks of pending users
            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'res.partner.kyc.approval'),
                ('res_id', '=', self.ids),
                ('user_id', 'in', pending.mapped('user_id').ids),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
            ])

            # Reset KYC state
            kyc.write({'assigned_to': None, 'state': 'draft'})

            # Notify creator
            kyc.env['bus.bus']._sendone(
                kyc.create_uid.partner_id,
                'simple_notification',
                {
                    'type': 'danger',
                    'title': _('KYC for %s suspended by %s. Start approval again.') %
                             (kyc.partner_id.name, self.env.user.name),
                    'message': '',
                    'sticky': True
                }
            )

            # Notify current user
            kyc.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': 'Approval suspended successfully.',
                    'message': '',
                    'sticky': True
                }
            )

            activities.unlink()


    # -------------------------------------------------------------------------
    # Reset to Draft
    # -------------------------------------------------------------------------
    def set_as_draft(self):
        """
        Reset KYC to draft:
            - Clear rejection fields
            - Reset approval workflow
        """
        self.write({
            'state': 'draft',
            'rejection_date': False,
            'rejection_reason': False,
            'is_rejected': False,
        })

        self.partner_id.sudo().write({
            'rejection_date': False,
            'rejection_reason': False,
            'is_rejected': False,
            'is_kyc': True,
        })

        self.approval_users_ids.write({'is_active': False})

    def _get_rekyc_snapshot(self):
        self.ensure_one()
        return {
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
            'partner_llp': self.partner_llp or False,
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
            # Overseas document expiry dates
            'company_reg_document': sorted(self.company_reg_document.ids),
            'authorized_person_id_document': sorted(self.authorized_person_id_document.ids),
            'company_reg_doc_expiry': str(self.company_reg_doc_expiry) if self.company_reg_doc_expiry else '',
            'authorized_person_id_expiry': str(self.authorized_person_id_expiry) if self.authorized_person_id_expiry else '',
            'directors_detail': [
                {
                    'designation': d.designation or '',
                    'name': d.name or '',
                    'contact_no': d.contact_no or '',
                    'email': d.email or '',
                    'aadhaar_card_attachments': sorted(d.aadhaar_card_attachments.ids),
                    'pan_card_attachments': sorted(d.pan_card_attachments.ids),
                    'govt_id_attachments': sorted(d.govt_id_attachments.ids),
                    'govt_id_expiry': str(d.govt_id_expiry) if d.govt_id_expiry else '',
                }
                for d in self.directors_detail
            ],
            'bank_detail': [
                {
                    'bank_name': b.bank_name or '',
                    'account_no': b.account_no or '',
                    'ifsc_code': b.ifsc_code or '',
                    # 'bank_address': b.bank_address or '',
                    'bank_cheque_attachments': sorted(b.bank_cheque_attachments.ids),
                }
                for b in self.bank_detail
            ],
            'address_detail': [
                {
                    'business_street': a.business_street or '',
                    'business_city': a.business_city or '',
                    'business_pincode': a.business_pincode or '',
                    'business_phone': a.business_phone or '',
                    'business_email': a.business_email or '',
                    'business_state_id': a.business_state_id.id if a.business_state_id else False,
                    'business_country_id': a.business_country_id.id if a.business_country_id else False,
                }
                for a in self.address_detail
            ],
        }

    def _build_rekyc_changes(self, new_payload):
        self.ensure_one()
        old_payload = self._get_rekyc_snapshot()
        labels = {
            'email': 'Email',
            'point_of_contact': 'Point of Contact',
            'poc_user': 'Point of Contact to Vendor',
            'business_legal_name': 'Business Legal Name',
            'is_same_trade_name': 'Trade Name Same as Legal Name',
            'business_trade_name': 'Business Trade Name',
            'const_business': 'Constitution of Business',
            'other_business': 'Other Business',
            'aadhaar_pan_link': 'Aadhaar PAN Link',
            'gst_no': 'GST Number',
            'license_registered': 'Licenses Registered',
            'udyam_number': 'Udyam Number',
            'gst_return_duration': 'Filing Frequency',
            'pan_no': 'PAN Number',
            'comp_google_loc': 'Google Location',
            'cin_no': 'CIN Number',
            'no_partner_director': 'Number of Directors/Partners',
            'moa_aoa': 'MOA/AOA',
            'electricity_bill': 'Electricity Bill',
            'pan_card_document': 'PAN Card Document',
            'incorporation_certificate': 'Incorporation Certificate',
            'gst_certificate': 'GST Certificate',
            'udyam_document': 'Udyam Document',
            'shop_act_document': 'Shop Act Document',
            'shop_photos': 'Shop Photos',
            'shop_videos': 'Shop Videos',
            'directors_detail': 'Director Details',
            'bank_detail': 'Bank Details',
            'address_detail': 'Address Details',
        }
        changes = []
        for key, label in labels.items():
            old_val = old_payload.get(key)
            new_val = new_payload.get(key)
            if old_val != new_val:
                changes.append({
                    'field': label,
                    'old': old_val,
                    'new': new_val,
                })
        return changes

    def _stringify_change_value(self, value):
        if value in (False, None, '', []):
            return 'Empty'
        if isinstance(value, bool):
            return 'Yes' if value else 'No'
        if isinstance(value, list):
            return f'{len(value)} item(s)'
        return str(value)

    def submit_rekyc_payload(self, payload, remark=''):
        self.ensure_one()
        if self.state != 'confirmed':
            raise ValidationError(_("Re-KYC can only be submitted for confirmed KYC records."))
        if not self.poc_user:
            raise ValidationError(_("Point of Contact to Vendor is required to submit Re-KYC for approval."))
        changes = self._build_rekyc_changes(payload)
        if not changes:
            raise ValidationError(_("No changes detected. Please update at least one field before submitting Re-KYC."))

        lines = []
        for ch in changes:
            lines.append(
                f"<li><b>{ch['field']}</b>: \"{self._stringify_change_value(ch['old'])}\" "
                f"&rarr; \"{self._stringify_change_value(ch['new'])}\"</li>"
            )

        self.write({
            'rekyc_state': 'pending',
            'rekyc_pending_payload': payload,
            'rekyc_requested_by': self.env.user.id,
            'rekyc_requested_on': fields.Datetime.now(),
            'rekyc_rejection_reason': False,
            'rekyc_rejected_by': False,
            'rekyc_rejected_on': False,
            'rekyc_approved_by': False,
            'rekyc_approved_on': False,
        })

        self.activity_schedule(
            act_type_xmlid='mail.mail_activity_data_todo',
            summary=f"Re-KYC Approval for: {self.partner_id.name}",
            note=_("Please review Re-KYC changes and approve/reject."),
            user_id=self.poc_user.id,
            date_deadline=fields.Date.context_today(self),
        )

        self.message_post(
            body=Markup(
                "<p><b>Re-KYC submitted for approval.</b></p>"
                f"<p><b>Reason:</b> {remark or 'N/A'}</p>"
                "<p><b>Changed fields:</b></p><ul>"
                + "".join(lines) +
                "</ul>"
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        # Send "Vendor Re-KYC Confirmation Request" email to the vendor
        if self.partner_id and self.partner_id.email:
            template = self.env.ref(
                'ks_contact.mail_template_vendor_rekyc_confirmation_request',
                raise_if_not_found=False,
            )
            if template:
                # Generate pre-filled survey URL from current KYC data and store
                # it on the partner so the email template can use object.rekyc_survey_url
                try:
                    if self.partner_id.is_overseas:
                        survey_url = self.partner_id._get_overseas_rekyc_survey_url()
                    else:
                        survey_url = self.partner_id._get_rekyc_survey_url()
                    self.partner_id.sudo().write({'rekyc_survey_url': survey_url})
                except Exception as e:
                    _logger.exception("Failed to generate Re-KYC survey URL for partner %s: %s",
                                      self.partner_id.id, e)
                template.send_mail(self.partner_id.id, force_send=True)

    def _rekyc_payload_to_write_vals(self, payload):
        write_vals = {
            'email': payload.get('email'),
            'point_of_contact': payload.get('point_of_contact'),
            'poc_user': payload.get('poc_user') or False,
            'business_legal_name': payload.get('business_legal_name'),
            'is_same_trade_name': bool(payload.get('is_same_trade_name')),
            'business_trade_name': payload.get('business_trade_name'),
            'const_business': payload.get('const_business'),
            'other_business': payload.get('other_business'),
            'aadhaar_pan_link': payload.get('aadhaar_pan_link'),
            'gst_no': payload.get('gst_no'),
            'license_registered': payload.get('license_registered'),
            'udyam_number': payload.get('udyam_number'),
            'gst_return_duration': payload.get('gst_return_duration'),
            'pan_no': payload.get('pan_no'),
            'comp_google_loc': payload.get('comp_google_loc'),
            'partner_llp': payload.get('partner_llp'),
            'cin_no': payload.get('cin_no'),
            'no_partner_director': payload.get('no_partner_director'),
            'moa_aoa': [(6, 0, payload.get('moa_aoa', []))],
            'electricity_bill': [(6, 0, payload.get('electricity_bill', []))],
            'pan_card_document': [(6, 0, payload.get('pan_card_document', []))],
            'incorporation_certificate': [(6, 0, payload.get('incorporation_certificate', []))],
            'gst_certificate': [(6, 0, payload.get('gst_certificate', []))],
            'udyam_document': [(6, 0, payload.get('udyam_document', []))],
            'shop_act_document': [(6, 0, payload.get('shop_act_document', []))],
            'shop_photos': [(6, 0, payload.get('shop_photos', []))],
            'shop_videos': [(6, 0, payload.get('shop_videos', []))],
            # Overseas KYC documents
            'company_reg_document': [(6, 0, payload.get('company_reg_document', []))],
            'authorized_person_id_document': [(6, 0, payload.get('authorized_person_id_document', []))],
            'company_reg_doc_expiry': payload.get('company_reg_doc_expiry') or False,
            'authorized_person_id_expiry': payload.get('authorized_person_id_expiry') or False,
            'directors_detail': [(5, 0, 0)] + [
                (0, 0, {
                    'designation': d.get('designation'),
                    'name': d.get('name'),
                    'contact_no': d.get('contact_no'),
                    'email': d.get('email'),
                    'aadhaar_card_attachments': [(6, 0, d.get('aadhaar_card_attachments', []))],
                    'pan_card_attachments': [(6, 0, d.get('pan_card_attachments', []))],
                    'govt_id_attachments': [(6, 0, d.get('govt_id_attachments', []))],
                    'govt_id_expiry': d.get('govt_id_expiry') or False,
                }) for d in payload.get('directors_detail', [])
            ],
            'bank_detail': [(5, 0, 0)] + [
                (0, 0, {
                    'bank_name': b.get('bank_name'),
                    'account_no': b.get('account_no'),
                    'ifsc_code': b.get('ifsc_code'),
                    # 'bank_address': b.get('bank_address'),
                    'bank_cheque_attachments': [(6, 0, b.get('bank_cheque_attachments', []))],
                }) for b in payload.get('bank_detail', [])
            ],
            'address_detail': [(5, 0, 0)] + [
                (0, 0, {
                    'business_street': a.get('business_street'),
                    'business_city': a.get('business_city'),
                    'business_pincode': a.get('business_pincode'),
                    'business_phone': a.get('business_phone'),
                    'business_email': a.get('business_email'),
                    'business_state_id': a.get('business_state_id') or False,
                    'business_country_id': a.get('business_country_id') or False,
                }) for a in payload.get('address_detail', [])
            ],
        }
        return write_vals

    def action_approve_rekyc(self):
        self.ensure_one()
        if self.rekyc_state != 'pending':
            raise ValidationError(_("No pending Re-KYC request found."))
        if self.env.user != self.poc_user:
            raise ValidationError(_("Only the configured Point of Contact can approve Re-KYC."))

        payload = self.rekyc_pending_payload or {}
        self.write(self._rekyc_payload_to_write_vals(payload))

        # When Re-KYC is approved, set deadline to exactly 1 year from current date
        deadline_date = fields.Date.context_today(self) + relativedelta(years=1)
        self.write({
            'rekyc_state': 'approved',
            'rekyc_approved_by': self.env.user.id,
            'rekyc_approved_on': fields.Datetime.now(),
            'rekyc_pending_payload': False,
            'deadline': deadline_date,
        })

        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'res.partner.kyc.approval'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.user.id),
            ('summary', 'ilike', 'Re-KYC Approval'),
        ])
        activities.unlink()

        self.message_post(
            body=Markup("<p><b>Re-KYC approved.</b> Pending changes applied to the existing KYC record.</p>"),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def action_open_rekyc_reject_wizard(self):
        self.ensure_one()
        return {
            'name': _('Reject Re-KYC'),
            'type': 'ir.actions.act_window',
            'res_model': 'rekyc.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_kyc_id': self.id,
            },
        }

    def action_reject_rekyc(self, reason):
        self.ensure_one()
        if self.rekyc_state != 'pending':
            raise ValidationError(_("No pending Re-KYC request found."))
        if self.env.user != self.poc_user:
            raise ValidationError(_("Only the configured Point of Contact can reject Re-KYC."))

        self.write({
            'rekyc_state': 'rejected',
            'rekyc_rejected_by': self.env.user.id,
            'rekyc_rejected_on': fields.Datetime.now(),
            'rekyc_rejection_reason': reason,
        })

        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'res.partner.kyc.approval'),
            ('res_id', '=', self.id),
            ('user_id', '=', self.env.user.id),
            ('summary', 'ilike', 'Re-KYC Approval'),
        ])
        activities.unlink()

        self.message_post(
            body=Markup(f"<p><b>Re-KYC rejected.</b><br/><b>Reason:</b> {reason}</p>"),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )


    # -------------------------------------------------------------------------
    # Approve by Manager
    # -------------------------------------------------------------------------
    def approve_by_manager(self):
        self.write({'state': 'confirmed'})


    # -------------------------------------------------------------------------
    # Sequential Approval Activities
    # -------------------------------------------------------------------------
    def _schedule_sequential_approval_activities(self):
        """
        Create activity only for the first pending approver (sequential approval).
        After first approver approves, activity will be created for the next approver.
        """
        for rec in self:
            # Get the first pending approver in sequence
            pending_approvers = sorted(
                rec.approval_users_ids.filtered(lambda l: not l.state),
                key=lambda l: l.sequence
            )
            
            if pending_approvers:
                first_approver = pending_approvers[0]
                
                # Create activity only for the first approver
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=f"KYC Approval for: {rec.partner_id.name}",
                    note=_("Please review this KYC approval request."),
                    user_id=first_approver.user_id.id,
                    date_deadline=fields.Date.context_today(rec),
                )

                # Send real-time notification to first approver
                rec.env['bus.bus']._sendone(
                    first_approver.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': _("KYC Approval for: %s") % rec.partner_id.name,
                        'message': _("A new approval task has been assigned to you."),
                        'sticky': True,
                    }
                )
                
                # Set assigned_to to first pending approver
                rec.assigned_to = first_approver.user_id

                # Send "Vendor KYC Approval Assignment" email to assigned approver
                if rec.assigned_to and rec.assigned_to.email:
                    template = rec.env.ref(
                        'ks_contact.assign_to_email_template',
                        raise_if_not_found=False,
                    )
                    if template:
                        template.send_mail(rec.id, force_send=True)

    # -------------------------------------------------------------------------
    # Assign next approver (sequential approval)
    # -------------------------------------------------------------------------
    def _update_assigned_to(self):
        """
        Determine the next approver based on sequence (sequential approval).
        After an approver approves, trigger activity for the next approver.
        """
        for rec in self:
            # Get the first pending approver in sequence
            pending_approvers = sorted(
                rec.approval_users_ids.filtered(lambda l: not l.state),
                key=lambda l: l.sequence
            )
            
            if pending_approvers:
                next_approver = pending_approvers[0]
                rec.assigned_to = next_approver.user_id

                # Send "Vendor KYC Approval Assignment" email to next assigned approver
                if rec.assigned_to and rec.assigned_to.email:
                    template = rec.env.ref(
                        'ks_contact.assign_to_email_template',
                        raise_if_not_found=False,
                    )
                    if template:
                        template.send_mail(rec.id, force_send=True)

                # Create activity for the next approver if not already exists
                existing_activity = self.env['mail.activity'].search([
                    ('res_model', '=', 'res.partner.kyc.approval'),
                    ('res_id', '=', rec.id),
                    ('user_id', '=', next_approver.user_id.id),
                    ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ], limit=1)
                
                if not existing_activity:
                    # Create activity for next approver
                    rec.activity_schedule(
                        act_type_xmlid='mail.mail_activity_data_todo',
                        summary=f"KYC Approval for: {rec.partner_id.name}",
                        note=_("Please review this KYC approval request."),
                        user_id=next_approver.user_id.id,
                        date_deadline=fields.Date.context_today(rec),
                    )
                    
                    # Send real-time notification to next approver
                    rec.env['bus.bus']._sendone(
                        next_approver.user_id.partner_id,
                        'simple_notification',
                        {
                            'type': 'success',
                            'title': _("KYC Approval for: %s") % rec.partner_id.name,
                            'message': _("A new approval task has been assigned to you."),
                            'sticky': True,
                        }
                    )
            else:
                rec.assigned_to = False


    # -------------------------------------------------------------------------
    # Approval Workflow State Checker
    # -------------------------------------------------------------------------
    def _update_state_based_on_approvals(self):
        """
        Recalculate KYC state based on all approval users (sequential approval):
            - Any reject → rejected
            - All approve → confirmed
        """
        for rec in self:
            active_lines = rec.approval_users_ids.filtered(lambda l: l.is_active)
            states = active_lines.mapped('state')

            if any(s == 'reject' for s in states):
                # Use write() to trigger proper state change logic
                rec.write({'state': 'rejected'})
            elif states and all(s == 'approve' for s in states):
                # All approvers have approved - confirm the KYC and set deadline to 1 year from today
                deadline_date = date.today() + relativedelta(years=1)
                rec.write({
                    'state': 'confirmed',
                    'deadline': deadline_date,
                })

                rec.unlink_expiry_activities()
                
                # Post chatter message indicating both levels approved
                approvers_info = []
                for line in sorted(active_lines, key=lambda l: l.sequence):
                    level = "Approver 1" if line.sequence == 1 else "Approver 2"
                    approvers_info.append(f"{level}: {line.user_id.name}")
                
                rec.message_post(
                    body=Markup(_("KYC Approved - All approval levels have been completed: %s ") % (
                        "</p>".join(approvers_info)
                    )),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )

    def unlink_expiry_activities(self):
        for rec in self:
            # 1. Find the activity on the Partner record
            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', rec.partner_id.id),
                ('summary', '=', 'KYC Expiry Follow-up')
            ])

            # 2. Delete them so they vanish from the list view
            if activities:
                activities.unlink()

    # -------------------------------------------------------------------------
    # Notification on rejection
    # -------------------------------------------------------------------------
    def _send_notification_on_rejection(self):
        """
        Notifies all approvers of rejection event.
        """
        config = self.env['vendor.approval.config'].get_config()
        if not config:
            return
        
        approval_users = config.get_all_approvers()

        for user in approval_users:
            msg = (
                f'Vendor approval request for {self.partner_id.name}, rejected by {self.env.user.name}.'
                if user != self.env.user else
                f'Vendor approval request for {self.partner_id.name}, successfully rejected by you.'
            )

            self.env['bus.bus']._sendone(
                user.partner_id,
                'simple_notification',
                {
                    'type': 'info',
                    'title': msg,
                    'message': '',
                    'sticky': True,
                }
            )


    # -------------------------------------------------------------------------
    # WRITE OVERRIDE (attachment linking + notifications)
    # -------------------------------------------------------------------------
    def write(self, vals):
        """
        Override Write:
            - Ensures attachments always link to record
            - Handles logic on state change:
                * confirmed → approval notifications
                * rejected → rejection activities
        """
        res = super().write(vals)

        # --- Attachments Management ---
        attachment_fields = [
            'gst_certificate', 'udyam_document', 'shop_act_document',
            'shop_photos', 'shop_videos', 'pan_card_document',
            'incorporation_certificate', 'moa_aoa', 'electricity_bill',
            'company_reg_document', 'authorized_person_id_document',
        ]

        for record in self:
            for field in attachment_fields:
                attachments = record[field]
                if attachments:
                    attachments.write({'res_model': self._name, 'res_id': record.id})

        # --- Helpers ---
        def _schedule_activity(record, user, title, note):
            """Schedule notification for rejection."""
            record.activity_schedule(
                act_type_xmlid='mail.mail_activity_data_todo',
                summary=title,
                note=note,
                user_id=user.id,
                date_deadline=fields.Date.context_today(record),
            )

        def _send_notification(record, user, title, message):
            """Realtime notifications (bus)."""
            record.env['bus.bus']._sendone(
                user.partner_id,
                'simple_notification',
                {
                    'type': 'warning',
                    'title': title,
                    'message': message,
                    'sticky': True,
                }
            )

        # --- Confirmed Logic ---
        for record in self:
            if vals.get('state') == 'confirmed':
                # Always set KYC deadline to exactly 1 year from current date when approved
                deadline_date = fields.Date.context_today(record) + relativedelta(years=1)
                now = fields.Datetime.now()
                record.write({
                    'approval_date': now,
                    'deadline': deadline_date,
                })

                if record.partner_id and not record.partner_id.is_approved:
                    # Update partner (deadline is computed from KYC on partner)
                    record.partner_id.write({
                        'is_approved': True,
                        'approval_status': 'approved',
                    })

                    # Notify all approvers
                    for user in record.existing_user_ids:
                        _send_notification(
                            record,
                            user,
                            _("KYC Approved for: %s") % record.partner_id.name,
                            _("KYC for %s has been approved.") % record.partner_id.name
                        )

            # --- Pending Logic: sync partner approval_status when KYC is submitted for approval ---
            elif vals.get('state') == 'pending':
                for record in self:
                    if record.partner_id and hasattr(record.partner_id, 'approval_status'):
                        record.partner_id.write({'approval_status': 'to_approve'})

            # --- Rejected Logic ---
            elif vals.get('state') == 'rejected':
                for record in self:
                    if record.partner_id and hasattr(record.partner_id, 'approval_status'):
                        record.partner_id.write({'approval_status': 'draft'})
                    for user in record.existing_user_ids:
                        _schedule_activity(
                            record, user,
                            f"KYC Rejected for: {record.partner_id.name}",
                            _("KYC for %s has been rejected.") % record.partner_id.name
                        )

        return res


# =============================================================================
# APPROVAL USERS MODEL
# =============================================================================
class ApprovalUsers(models.Model):
    """
    Lines indicating approval sequence + approver decision.
    """
    _name = "approval.users"
    _description = "Approval Users"
    _order = "sequence"
    _rec_name = "kyc_approval_id"

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval')
    sequence = fields.Integer()
    job_id = fields.Char("Designation", readonly=True)
    user_id = fields.Many2one('res.users', string='User', required=True)

    state = fields.Selection([
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('suspended', 'Suspended')
    ])

    remark = fields.Text('Remarks', tracking=True)
    action_date = fields.Datetime()
    group = fields.Selection([
        ('group1', 'Group 1'),
        ('group2', 'Group 2'),
    ])
    is_active = fields.Boolean(default=True)

    def write(self, vals):
        """
        On any update, reevaluate KYC state.
        """
        res = super().write(vals)
        if self.kyc_approval_id:
            self.kyc_approval_id._update_state_based_on_approvals()
        return res

    @api.model
    def create(self, vals):
        """
        Auto update KYC state after approver created.
        """
        res = super().create(vals)
        if res.kyc_approval_id:
            res.kyc_approval_id._update_state_based_on_approvals()
        return res


# =============================================================================
# DIRECTOR DETAILS
# =============================================================================
class DirectorDetails(models.Model):
    """
    Director-level information + attachments.
    """
    _name = "director.details"
    _rec_name = 'name'
    _description = "Directors Details"

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval')

    designation = fields.Char()
    name = fields.Char()
    contact_no = fields.Char()
    email = fields.Char()

    # These are binary fields from survey
    aadhaar_card = fields.Binary()
    aadhaar_card_filename = fields.Char()
    pan_card = fields.Binary()
    pan_card_filename = fields.Char()

    # Many2many attachments
    aadhaar_card_attachments = fields.Many2many(
        'ir.attachment', 'vendor_bank_aadhaar_card_rel',
        'kyc_approval_id', 'attachment_id'
    )

    pan_card_attachments = fields.Many2many(
        'ir.attachment', 'vendor_bank_pan_card_rel',
        'kyc_approval_id', 'attachment_id'
    )

    # Overseas: government-issued identity document (Passport, Emirates ID, HKID, etc.)
    govt_id_attachments = fields.Many2many(
        'ir.attachment', 'director_details_govt_id_rel',
        'director_id', 'attachment_id',
        string="Govt. ID (Passport / Emirates ID / HKID)",
    )
    govt_id_expiry = fields.Date(
        string="Govt. ID Expiry Date",
        help="Expiry date of this director's government-issued identity document.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Links Aadhaar / PAN / Govt ID attachments correctly.
        """
        res_list = super().create(vals_list)

        for record in res_list:
            for attachment in (
                record.aadhaar_card_attachments
                | record.pan_card_attachments
                | record.govt_id_attachments
            ):
                attachment.write({
                    'res_model': self._name,
                    'res_id': record.id,
                })

        return res_list


# =============================================================================
# BANK DETAILS
# =============================================================================
class BankDetail(models.Model):
    """
    Vendor bank detail with cheque attachments.
    """
    _name = "bank.details"
    _rec_name = 'bank_name'
    _description = "Bank Details"

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval')
    bank_name = fields.Char()
    account_no = fields.Char()
    ifsc_code = fields.Char()
    bank_address = fields.Char()

    bank_cheque_attachments = fields.Many2many(
        'ir.attachment', 'vendor_bank_detail_cheque_rel',
        'kyc_approval_id', 'attachment_id'
    )

    @api.model_create_multi
    def create(self, vals_list):
        res_list = super().create(vals_list)

        for record in res_list:
            record.bank_cheque_attachments.write({
                'res_model': self._name,
                'res_id': record.id
            })

        return res_list


# =============================================================================
# ADDRESS DETAILS
# =============================================================================
class AddressDetail(models.Model):
    """
    Principal place of business address.
    """
    _name = "address.details"
    _description = "Address Details"
    _rec_name = 'kyc_approval_id'

    kyc_approval_id = fields.Many2one('res.partner.kyc.approval')

    business_street = fields.Char("Address")
    business_city = fields.Char("City")
    business_pincode = fields.Char("Pincode")
    business_phone = fields.Char("Contact Number")
    business_email = fields.Char("Email Address")

    business_state_id = fields.Many2one(
        'res.country.state',
        string='Business State',
        domain="[('country_id', '=?', business_country_id)]"
    )

    business_country_id = fields.Many2one(
        'res.country', string='Business Country'
    )
