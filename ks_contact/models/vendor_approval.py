# -*- coding: utf-8 -*-

from datetime import date
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
    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to:
        - Create KYC record
        - Link attachments to `res.partner.kyc.approval`
        """
        res_list = super().create(vals_list)

        attachment_fields = [
            'gst_certificate', 'udyam_document', 'shop_act_document',
            'shop_photos', 'shop_videos', 'pan_card_document',
            'incorporation_certificate', 'moa_aoa', 'electricity_bill'
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

    @api.depends('approval_users_ids.user_id', 'approval_users_ids.state')
    @api.depends_context('uid')
    def _compute_has_pending_approval(self):
        """Check if current user has a pending approval request"""
        current_user = self.env.user
        for record in self:
            pending_line = record.approval_users_ids.filtered(
                lambda l: l.user_id == current_user and not l.state
            )
            record.has_pending_approval = bool(pending_line)


    # -------------------------------------------------------------------------
    # KYC Fields
    # -------------------------------------------------------------------------

    partner_id = fields.Many2one('res.partner', string="Contact", tracking=True)
    email = fields.Char("Email", tracking=True)
    point_of_contact = fields.Char("Point of Contact / Purchase Manager (Bora Multicorp)", tracking=True)
    poc_user = fields.Many2one('res.users', string="Point of Contact to Vendor", tracking=True)
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
                                        string='Aadhar and PAN card linking?',
                                        required=True)

    gst_no = fields.Char("GST Number", required=True)
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
    ], string="GST Return duration")

    shop_photos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_photos_rels',
                                   'partner_id', 'attachment_id', string="Shop Photos")

    shop_videos = fields.Many2many('ir.attachment', 'vendor_kyc_shop_videos_rels',
                                   'partner_id', 'attachment_id', string="Shop Videos")

    no_partner_director = fields.Selection([(str(x), str(x)) for x in range(1, 8)],
                                           string="No. of Managing Partner / Directors")

    directors_detail = fields.One2many('director.details', 'kyc_approval_id', string="KYC Details", tracking=True)
    pan_no = fields.Char("PAN Number", required=True)
    comp_google_loc = fields.Char("Google Location of Shop")
    partner_llp_filename = fields.Char()
    partner_llp = fields.Binary("Partnership/LLP Deed")

    moa_aoa = fields.Many2many('ir.attachment', 'vendor_kyc_moa_aoa_rels',
                               'partner_id', 'attachment_id', string="MOA/AOA")

    cin_no = fields.Char("CIN number")
    electricity_bill = fields.Many2many('ir.attachment', 'vendor_kyc_electricity_bill_rels',
                                        'partner_id', 'attachment_id', string="Electricity bill")

    incorporation_certificate = fields.Many2many('ir.attachment', 'incorportaion_certificate_rels',
                                                 'partner_id', 'attachment_id', string="Incorporation Certificate")

    bank_detail = fields.One2many('bank.details', 'kyc_approval_id', string="Banks Detail")
    address_detail = fields.One2many('address.details', 'kyc_approval_id', string="Address Detail")

    deadline = fields.Date('Deadline Date', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected')
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

    is_approved = fields.Boolean(related='partner_id.is_approved', store=True)

    approval_date = fields.Datetime("Approval Date", tracking=True)
    is_rejected = fields.Boolean(tracking=True)
    rejection_date = fields.Datetime("Rejection Date", tracking=True)
    rejection_reason = fields.Text('Rejection Reason', tracking=True)

    can_set_draft = fields.Boolean(
        compute="_compute_can_set_draft", string="Can Set Draft"
    )

    # -------------------------------------------------------------------------
    # Compute draft button visibility
    # -------------------------------------------------------------------------
    def _compute_can_set_draft(self):
        """
        Only creator or non-approvers can set back to draft.
        Approvers should not edit their own approval workflow.
        """
        for rec in self:
            rec.can_set_draft = not (self.env.user in rec.approval_users_ids.mapped('user_id'))

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

        self.write({'approval_users_ids': vals, 'state': 'pending'})
        
        # Create activities for ALL approvers simultaneously (parallel approval)
        self._schedule_parallel_approval_activities()

    # -------------------------------------------------------------------------
    # Submit KYC Approval
    # -------------------------------------------------------------------------
    def confirm_submit_form(self):
        """Submit KYC for approval - accessible to all users"""
        # Check if approval config exists (read-only check, no sudo needed for read)
        config = self.env['vendor.approval.config'].get_config()
        if not config:
            raise ValidationError(_("Please configure Approval Authority in Vendor Approval Settings before Submit Request"))

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


    # -------------------------------------------------------------------------
    # Approve by Manager
    # -------------------------------------------------------------------------
    def approve_by_manager(self):
        self.write({'state': 'confirmed'})


    # -------------------------------------------------------------------------
    # Parallel Approval Activities
    # -------------------------------------------------------------------------
    def _schedule_parallel_approval_activities(self):
        """
        Create activities for ALL pending approvers simultaneously (parallel approval).
        Each approver receives their own activity and can act independently.
        """
        for rec in self:
            pending_approvers = rec.approval_users_ids.filtered(lambda l: not l.state)
            
            for approver_line in pending_approvers:
                # Create activity for each approver
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=f"KYC Approval for: {rec.partner_id.name}",
                    note=_("Please review this KYC approval request."),
                    user_id=approver_line.user_id.id,
                    date_deadline=fields.Date.context_today(rec),
                )

                # Send real-time notification to each approver
                rec.env['bus.bus']._sendone(
                    approver_line.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': _("KYC Approval for: %s") % rec.partner_id.name,
                        'message': _("A new approval task has been assigned to you."),
                        'sticky': True,
                    }
                )
            
            # Set assigned_to to first pending approver for backward compatibility
            # (but all approvers can see buttons via has_pending_approval)
            if pending_approvers:
                rec.assigned_to = pending_approvers[0].user_id

    # -------------------------------------------------------------------------
    # Assign next approver (kept for backward compatibility, but not used in parallel flow)
    # -------------------------------------------------------------------------
    def _update_assigned_to(self):
        """
        Determine the next approver based on sequence.
        Note: In parallel approval flow, this is mainly for backward compatibility.
        All pending approvers can act independently via has_pending_approval.
        """
        for rec in self:
            next_user = next(
                (line.user_id for line in sorted(rec.approval_users_ids, key=lambda l: l.sequence)
                 if not line.state),
                None
            )

            rec.assigned_to = next_user


    # -------------------------------------------------------------------------
    # Approval Workflow State Checker
    # -------------------------------------------------------------------------
    def _update_state_based_on_approvals(self):
        """
        Recalculate KYC state based on all approval users (parallel approval):
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
                # All approvers have approved - confirm the KYC
                # Use write() to trigger proper state change logic and activity updates
                # The write() method will handle partner updates, activity removal, and notifications
                rec.write({'state': 'confirmed'})
                
                # Post chatter message indicating both levels approved
                approvers_info = []
                for line in sorted(active_lines, key=lambda l: l.sequence):
                    level = "Approval Level 1" if line.sequence == 1 else "Approval Level 2"
                    approvers_info.append(f"{level}: {line.user_id.name}")
                
                rec.message_post(
                    body=Markup(_("KYC Approved - All approval levels have been completed: %s ") % (
                        "</p>".join(approvers_info)
                    )),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )


    # -------------------------------------------------------------------------
    # Notification on rejection
    # -------------------------------------------------------------------------
    def _send_notification_on_rejection(self):
        """
        Notifies all approvers of rejection event.
        """
        approval_users = self.env['vendor.approval.config'].sudo().search([])

        for user in approval_users:
            msg = (
                f'Vendor approval request for {self.partner_id.name}, rejected by {self.env.user.name}.'
                if user.user_id != self.env.user else
                f'Vendor approval request for {self.partner_id.name}, successfully rejected by you.'
            )

            self.env['bus.bus']._sendone(
                user.user_id.partner_id,
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
            'incorporation_certificate', 'moa_aoa', 'electricity_bill'
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

                if record.partner_id and not record.partner_id.is_approved:
                    now = fields.Datetime.now()
                    one_year = now + relativedelta(years=1)

                    # Update partner and record
                    record.partner_id.write({
                        'is_approved': True,
                        'deadline': one_year,
                    })
                    record.write({
                        'approval_date': now,
                        'deadline': one_year,
                    })

                    # Notify all approvers
                    for user in record.existing_user_ids:
                        _send_notification(
                            record,
                            user,
                            _("KYC Approved for: %s") % record.partner_id.name,
                            _("KYC for %s has been approved.") % record.partner_id.name
                        )

            # --- Rejected Logic ---
            elif vals.get('state') == 'rejected':
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

    @api.model_create_multi
    def create(self, vals_list):
        """
        Links Aadhaar / PAN attachments correctly.
        """
        res_list = super().create(vals_list)

        for record in res_list:
            for attachment in record.aadhaar_card_attachments | record.pan_card_attachments:
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
