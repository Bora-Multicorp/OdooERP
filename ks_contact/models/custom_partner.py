# -*- coding: utf-8 -*-
import logging
import re
from datetime import timedelta, date
from lxml import etree
from odoo.exceptions import ValidationError

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class CustomContact(models.Model):
    _inherit = 'res.partner'

    _sql_constraints = [
        # SQL-level constraint (optional if email is NULLable)
        ('unique_email', 'UNIQUE(email)', 'Email address must be unique.')
    ]

    is_expired = fields.Boolean(compute='_compute_is_expired')

    @api.depends('deadline')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            # Check if deadline is in the past
            rec.is_expired = rec.deadline and rec.deadline <= today

    @api.constrains('city', 'zip')
    def _check_city_zip_format(self):
        """
        Validate city and zip/pincode formatting.

        City:
            - Must contain only letters, spaces, or hyphens.
            - Regex: ^[A-Za-z\s\-]+$

        Zip (Pincode):
            - Must be exactly 6 digits.
            - Regex: ^\d{6}$

        Raises
        ------
        ValidationError:
            If city or pincode does not match the required format.
        """
        city_regex = re.compile(r"^[A-Za-z\s\-]+$")
        zip_regex = re.compile(r"^\d{6}$")

        for rec in self:
            # Validate City
            if rec.city and not city_regex.match(rec.city):
                raise ValidationError(
                    _("City must contain only letters, spaces, or hyphens.\nInvalid Value: %s") % rec.city
                )

            # Validate Pincode (6 digits)
            if rec.zip and not zip_regex.match(rec.zip):
                raise ValidationError(
                    _("Pincode must be exactly 6 digits (e.g., 400001).\nInvalid Value: %s") % rec.zip
                )

    @api.constrains('email')
    def _check_duplicate_email(self):
        """
        Validate email format and ensure uniqueness.

        Email:
            - Must follow a basic valid pattern.
            - Regex: ^[\w\.-]+@[\w\.-]+\.\w+$
            - Must be unique across all partners (case-insensitive).

        Raises
        ------
        ValidationError:
            If email format is invalid or the email is already assigned
            to another partner.
        """
        email_regex = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')

        for rec in self:
            email = rec.email

            # Skip if no email set
            if not email:
                continue

            # Validate email format
            if not email_regex.match(email):
                raise ValidationError(
                    _("Invalid email format: %s. Expected format: user@example.com.") % email
                )

            # Check duplicate email (case insensitive)
            existing = self.env['res.partner'].search([
                ('email', '=ilike', email),
                ('id', '!=', rec.id)
            ], limit=1)

            if existing:
                raise ValidationError(
                    _("The email address '%s' is already used by another contact.") % email
                )

    @api.constrains('l10n_in_pan')
    def _check_pan_card_no_format(self):
        """
        Validate Indian PAN number format and enforce uniqueness.

        PAN Format:
            - 5 uppercase letters
            - 4 digits
            - 1 uppercase letter
            Example: ABCDE1234F

        Raises
        ------
        ValidationError:
            If PAN format is invalid or duplicate PAN is found.
        """
        pan_regex = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')

        for rec in self:
            pan = (rec.l10n_in_pan or "").upper()

            # Skip empty PAN
            if not pan:
                continue

            # Validate PAN format
            if not pan_regex.match(pan):
                raise ValidationError(
                    _("Invalid PAN format: %s. Expected format: ABCDE1234F.") % rec.l10n_in_pan
                )

            # Validate uniqueness (case-insensitive)
            duplicate = self.search([
                ('l10n_in_pan', '=ilike', pan),
                ('id', '!=', rec.id)
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    _("PAN number '%s' is already assigned to another contact.") % rec.l10n_in_pan
                )

    # @api.constrains('is_customer', 'is_vendor')
    # def _check_customer_vendor_exclusive(self):
    #     for rec in self:
    #         if rec.is_customer and rec.is_vendor:
    #             raise ValidationError(
    #                 "A partner cannot be both a Customer and a Vendor. Please uncheck one."
    #             )

    @api.constrains('is_vendor', 'vendor_type')
    def _check_vendor_type_required(self):
        """Vendor Type is required when Is Vendor is checked. Must be one of Regular, Exceptional, Operational."""
        for rec in self:
            if rec.is_vendor and rec.vendor_type not in ('regular', 'exceptional', 'operational'):
                raise ValidationError(
                    _("Vendor Type is required when the contact is marked as a Vendor. Please select Regular, Exceptional, or Operational.")
                )

    @api.constrains('vat')
    def _check_gst_no_format(self):
        gst_pattern = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')
        for rec in self:
            if rec.vat and not gst_pattern.match(rec.vat.upper()):
                raise ValidationError(_(
                    "Invalid GST Number: '%s'. It must follow the 15-character format (e.g., 27ABCDE1234F1Z5)."
                ) % rec.vat)

    @api.constrains('mobile', 'country_id')
    def _check_mobile_number_format(self):
        for rec in self:
            if not rec.mobile:
                continue

            # 1) First check country is added or not
            if not rec.country_id or not rec.country_id.phone_code:
                raise ValidationError(
                    "Please select a Country before entering the mobile number so we can verify the format."
                )

            # 2) Strip non-digits (like +, -, spaces)
            cleaned_number = re.sub(r'\D', '', rec.mobile)

            # 3) Remove leading country code
            code = str(rec.country_id.phone_code)
            if cleaned_number.startswith(code):
                cleaned_number = cleaned_number[len(code):]
            elif cleaned_number.startswith('0') and len(cleaned_number) > 10:
                # Optional: Handle leading zeros if necessary
                cleaned_number = cleaned_number[1:]

            # 4) Validate exactly 10 digits
            if not re.fullmatch(r'\d{10}', cleaned_number):
                raise ValidationError(
                    f"After removing the country code (+{code}), the mobile number must be exactly 10 digits. "
                    f"Currently, it is {len(cleaned_number)} digits."
                )

    @api.constrains('phone', 'country_id')
    def _check_phone_number_format(self):
        for rec in self:
            if not rec.phone:
                continue

            # 1) Remove all non-digits
            cleaned_number = re.sub(r'\D', '', rec.phone)

            # 2) Remove country code if present
            if rec.country_id and rec.country_id.phone_code:
                code = str(rec.country_id.phone_code)
                if code and cleaned_number.startswith(code):
                    cleaned_number = cleaned_number[len(code):]

            # 3) Validate exactly 10 digits
            if not re.fullmatch(r'\d{10}', cleaned_number):
                raise ValidationError(
                    _("Phone number must be exactly 10 digits after removing the country code.")
                )

    @api.onchange('country_id')
    def _onchange_country_mobile(self):
        if self.country_id:
            # Get the country calling code and ensure it starts with '+'
            calling_code = str(self.country_id.phone_code) if self.country_id.phone_code else ''
            if calling_code and not calling_code.startswith('+'):
                calling_code = '+' + calling_code

            if self.mobile:
                # Remove any existing country code at the start (e.g., +91 or +1)
                # Then remove all spaces
                self.mobile = re.sub(r'^\+\d+', '', self.mobile).replace(' ', '').strip()


    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id, view_type, **options)
        if 'action_id' in options:
            vendor_action = self.env.ref('account.res_partner_action_supplier', raise_if_not_found=False)

            # ✅ Only disable "New" button on Vendor action
            if vendor_action and vendor_action.id == options['action_id']:
                root = etree.fromstring(result['arch'])
                root.set('create', 'false')  # removes "New" button
                result['arch'] = etree.tostring(root)

        return result

    custom_type = fields.Many2one('res.partner.location.type', string="Type", tracking=True,
                                  help='Contact Location Type', copy=False)
    custom_address_type = fields.Many2one('res.partner.address.type', string="Address Type", tracking=True,
                                          help='Contact Address Type', copy=False)
    tally_name = fields.Char(string="Tally Name", tracking=True)
    purpose = fields.Char(string="Purpose", tracking=True)
    # Customer/Vendor KYC Details
    is_vendor = fields.Boolean(string="Is Vendor?", tracking=True)
    vendor_type = fields.Selection(
        [
            ('regular', 'Regular'),
            ('exceptional', 'Exceptional'),
            ('operational', 'Operational'),
        ],
        string='Vendor Type',
        tracking=True,
        copy=False,
        help='Required for vendors. Exceptional and Operational vendors skip KYC data entry but still go through approval.',
    )
    approval_status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('to_approve', 'To Approve'),
            ('approved', 'Approved'),
        ],
        string='Approval Status',
        default='draft',
        tracking=True,
        copy=False,
        help='Vendor approval workflow. Submit for Approval moves Draft → To Approve.',
    )
    is_customer = fields.Boolean(string="Is Customer?", tracking=True)
    is_kyc = fields.Boolean(string="Is KYC?", tracking=True)
    is_approved = fields.Boolean(string="Is Approved?", tracking=True)
    approval_date = fields.Datetime(string="Approval Date", tracking=True)
    is_rejected = fields.Boolean(string="Is Rejected?", tracking=True)
    rejection_date = fields.Datetime(string="Rejection Date", tracking=True)
    rejection_reason = fields.Text('Rejection Reason', tracking=True)
    deadline = fields.Date(
        string='KYC Deadline',
        compute='_compute_deadline',
        store=True,
        readonly=True,
        tracking=True,
        help='Fetched from the confirmed KYC approval deadline.',
    )

    kyc_details = fields.One2many('res.partner.kyc.approval', 'partner_id', string="KYC Details", tracking=True)

    @api.depends('kyc_details', 'kyc_details.state', 'kyc_details.deadline')
    def _compute_deadline(self):
        for rec in self:
            confirmed = rec.kyc_details.filtered(lambda k: k.state == 'confirmed')
            if confirmed:
                # Use the confirmed KYC with the latest deadline (or latest id)
                with_deadline = confirmed.filtered(lambda k: k.deadline)
                if with_deadline:
                    rec.deadline = max(with_deadline, key=lambda k: (k.deadline, k.id)).deadline
                else:
                    rec.deadline = False
            else:
                rec.deadline = False

    kyc_record_url = fields.Char(
        string='Record URL',
        compute='_compute_kyc_record_url',
        help='Direct link to this contact form in Odoo (for KYC expiry emails).',
    )

    def _compute_kyc_record_url(self):
        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        for rec in self:
            rec.kyc_record_url = f"{base}/web#id={rec.id}&model=res.partner&view_type=form" if base else ''

    # Contact (partner) approval flow — same as KYC but on Contact
    approval_line_ids = fields.One2many(
        'res.partner.approval.line',
        'partner_id',
        string='Approval Authorities',
        help='Approvers for this contact (sequential: Approver 1 then Approver 2).',
    )
    has_pending_approval = fields.Boolean(
        string='Has Pending Approval',
        compute='_compute_has_pending_approval',
        help='True if current user is the first pending approver for this contact.',
    )

    @api.depends('approval_line_ids.user_id', 'approval_line_ids.state', 'approval_line_ids.is_active')
    @api.depends_context('uid')
    def _compute_has_pending_approval(self):
        """Same logic as KYC: only first pending approver (by sequence) sees Approve/Reject."""
        current_user = self.env.user
        for record in self:
            pending = sorted(
                record.approval_line_ids.filtered(lambda l: l.is_active and not l.state),
                key=lambda l: l.sequence
            )
            if pending and pending[0].user_id.id == current_user.id:
                record.has_pending_approval = True
            else:
                record.has_pending_approval = False

    def _schedule_sequential_approval_activities(self):
        """Schedule activity only for the first pending approver (same as KYC)."""
        for rec in self:
            pending = sorted(
                rec.approval_line_ids.filtered(lambda l: l.is_active and not l.state),
                key=lambda l: l.sequence
            )
            if pending:
                first = pending[0]
                rec.activity_schedule(
                    act_type_xmlid='mail.mail_activity_data_todo',
                    summary=_("Vendor Approval: %s") % rec.name,
                    note=_("Please review this vendor approval request."),
                    user_id=first.user_id.id,
                    date_deadline=fields.Date.context_today(rec),
                )
                rec.env['bus.bus']._sendone(
                    first.user_id.partner_id,
                    'simple_notification',
                    {
                        'type': 'success',
                        'title': _("Vendor Approval: %s") % rec.name,
                        'message': _("A new approval task has been assigned to you."),
                        'sticky': True,
                    }
                )

    def _update_assigned_to_partner_approval(self):
        """After an approver approves: schedule activity for next approver or mark approved."""
        for rec in self:
            pending = sorted(
                rec.approval_line_ids.filtered(lambda l: l.is_active and not l.state),
                key=lambda l: l.sequence
            )
            if pending:
                next_approver = pending[0]
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'res.partner'),
                    ('res_id', '=', rec.id),
                    ('user_id', '=', next_approver.user_id.id),
                    ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ], limit=1)
                if not existing:
                    rec.activity_schedule(
                        act_type_xmlid='mail.mail_activity_data_todo',
                        summary=_("Vendor Approval: %s") % rec.name,
                        note=_("Please review this vendor approval request."),
                        user_id=next_approver.user_id.id,
                        date_deadline=fields.Date.context_today(rec),
                    )
                    rec.env['bus.bus']._sendone(
                        next_approver.user_id.partner_id,
                        'simple_notification',
                        {
                            'type': 'success',
                            'title': _("Vendor Approval: %s") % rec.name,
                            'message': _("A new approval task has been assigned to you."),
                            'sticky': True,
                        }
                    )
            else:
                # All approved — set partner approved and remove activities
                rec.sudo().write({
                    'approval_status': 'approved',
                    'is_approved': True,
                    'supplier_rank': 1,
                    'approval_date': fields.Datetime.now(),
                })
                self.env['mail.activity'].search([
                    ('res_model', '=', 'res.partner'),
                    ('res_id', '=', rec.id),
                    ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ]).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        """Set is_kyc when vendor_type is exceptional/operational so KYC form is skipped (approval flow still required)."""
        for vals in vals_list:
            if vals.get('is_vendor') and vals.get('vendor_type') in ('exceptional', 'operational'):
                vals['is_kyc'] = True
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        if vals.get('vendor_type') in ('1', '2'):
            vals['vendor_type'] = 'regular' if vals['vendor_type'] == '1' else 'exceptional'
        if 'vendor_type' not in vals:
            for rec in self:
                if rec.vendor_type == '1':
                    super(CustomContact, rec).write({'vendor_type': 'regular'})
                elif rec.vendor_type == '2':
                    super(CustomContact, rec).write({'vendor_type': 'exceptional'})
        # Detect Exceptional/Operational → Regular switch (for KYC reset)
        type_bypass_to_regular = {}
        if vals.get('vendor_type') == 'regular':
            for record in self:
                if record.vendor_type in ('exceptional', 'operational'):
                    type_bypass_to_regular[record.id] = True

        res = super().write(vals)

        for record in self:
            # If marked as Customer → directly set customer_rank (no approval needed)
            if vals.get('is_customer') or record.is_customer:
                if record.customer_rank != 1:
                    super(CustomContact, record.sudo()).write({'customer_rank': 1})

            # If marked as Vendor → require approval (or set when approval_status becomes approved)
            if vals.get('is_approved') is True and (vals.get('is_vendor') or record.is_vendor):
                if record.supplier_rank != 1:
                    super(CustomContact, record.sudo()).write({'supplier_rank': 1})

            # When approval_status is set to 'approved', set is_approved and supplier_rank
            if vals.get('approval_status') == 'approved':
                if not record.is_approved or record.supplier_rank != 1:
                    super(CustomContact, record.sudo()).write({
                        'is_approved': True,
                        'supplier_rank': 1,
                    })

            # KYC bypass for Exceptional/Operational: only skip KYC data entry (set is_kyc so form is not required).
            # Do NOT set is_approved — they must go through Submit for Approval → approval flow.
            if record.is_vendor and record.vendor_type in ('exceptional', 'operational'):
                if not record.is_kyc:
                    super(CustomContact, record.sudo()).write({'is_kyc': True})
            # When switching from Exceptional/Operational to Regular: clear KYC if no real KYC record
            elif type_bypass_to_regular.get(record.id):
                kyc_confirmed = record.kyc_details.filtered(lambda k: k.state == 'confirmed')
                if not kyc_confirmed and (record.is_kyc or record.is_approved):
                    super(CustomContact, record.sudo()).write({
                        'is_kyc': False,
                        'is_approved': False,
                    })

        return res

    def action_submit_for_approval(self):
        """
        Submit for Approval: approval for Contact (same UX as KYC).
        Opens "Select Approval Users" wizard (Approver 1 & 2); creates approval lines on partner
        and sets approval_status to 'to_approve'. No KYC record is used for this flow.
        """
        self.ensure_one()
        if not self.is_vendor:
            raise ValidationError(_("Only vendors can be submitted for approval."))
        if self.approval_status not in ('draft', False):
            raise ValidationError(_("Only draft vendors can be submitted for approval."))

        config = self.env['vendor.approval.config'].get_config()
        if not config:
            raise ValidationError(_("Please configure Vendor Approval Settings before submitting for approval."))
        if config.ks_approval_mode == 'two_way':
            if not config.ks_approver_1_ids or not config.ks_approver_2_ids:
                raise ValidationError(_("Please configure both Approver 1 and Approver 2 in Vendor Approval Settings."))
        else:
            if not config.ks_approver_1_ids:
                raise ValidationError(_("Please configure Approver 1 in Vendor Approval Settings."))

        return {
            'name': _('Select Approval Users'),
            'type': 'ir.actions.act_window',
            'res_model': 'partner.approval.user.picker.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id},
        }

    def _prepare_minimal_kyc_vals(self):
        """Prepare values for a minimal KYC record used only for the approval workflow (e.g. Exceptional/Operational)."""
        self.ensure_one()
        return {
            'partner_id': self.id,
            'state': 'draft',
            'email': self.email or '',
            'point_of_contact': self.name or '',
            'business_legal_name': self.name or 'N/A',
            'is_same_trade_name': True,
            'business_trade_name': self.name or 'N/A',
            'gst_no': self.vat or 'N/A',
            'pan_no': self.l10n_in_pan or 'N/A',
            'aadhaar_pan_link': 'no',
            'comp_google_loc': 'N/A',
            'const_business': 'Other',
            'other_business': 'N/A',
        }

    def action_approve_vendor(self):
        """Approve vendor: set approval_status to 'approved', is_approved and supplier_rank. Used for vendors who skipped KYC or after review."""
        for rec in self:
            if not rec.is_vendor:
                raise ValidationError(_("Only vendors can be approved."))
            if rec.approval_status != 'to_approve':
                raise ValidationError(_("Only vendors in 'To Approve' state can be approved."))
        self.sudo().write({
            'approval_status': 'approved',
            'is_approved': True,
            'supplier_rank': 1,
        })
        return True

    survey_ids = fields.One2many('survey.user_input', 'partner_id', string='Surveys')
    survey_count = fields.Integer(string="Survey Count",
                                  groups='sales_team.group_sale_salesman',
                                  compute='_compute_survey_count')

    def _compute_survey_count(self):
        for partner in self:
            if not self.env.user._has_group('sales_team.group_sale_salesman'):
                partner.survey_count = 0
                continue

            # Get self and child partners
            all_partners = self.with_context(active_test=False).search([('id', 'child_of', partner.id)])
            partner_ids = all_partners.ids
            partner_emails = [p.email for p in all_partners if p.email]

            # Search for surveys by partner_id or email
            domain = ['|',
                      ('partner_id', 'in', partner_ids),
                      ('email', 'in', partner_emails)]

            survey_count = self.env['survey.user_input'].with_context(active_test=False).search_count(domain)
            partner.survey_count = survey_count

    def action_view_survey_response(self):
        '''
        This function returns an action that displays the survey response from partner.
        '''
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_user_input')
        action['domain'] = ['|', ('partner_id', '=', self.id), ('email', '=', self.email)]
        return action

    @api.model
    def trigger_schedule_activity_kyc_expiry_follow_up(self):
        today = fields.Date.context_today(self)

        activity_type = self.env.ref('mail.mail_activity_data_todo')
        partner_model = self.env['res.partner']
        activity_model = self.env['mail.activity']
        partner_model_id = self.env.ref('base.model_res_partner').id

        # 1️⃣ Partners whose KYC expires today → schedule follow-up activity
        partners_today = partner_model.search([
            ('deadline', '=', today),
        ])

        for partner in partners_today:
            existing_activity = activity_model.search([
                ('res_model_id', '=', partner_model_id),
                ('res_id', '=', partner.id),
                ('summary', '=', 'KYC Expiry Follow-up'),
            ], limit=1)

            if not existing_activity:
                activity_model.create({
                    'activity_type_id': activity_type.id,
                    'summary': 'KYC Expiry Follow-up',
                    'note': f'KYC for {partner.name} expires today. Please re-verify.',
                    'date_deadline': today,
                    'user_id': partner.user_id.id or self.env.user.id,
                    'res_model_id': partner_model_id,
                    'res_id': partner.id,
                })

        # 2️⃣ Expired contacts (deadline < today): send KYC Expired email once per contact
        expired_partners = partner_model.search([
            ('deadline', '!=', False),
            ('deadline', '<', today),
            ('email', '!=', False),
        ])
        template = self.env.ref(
            'ks_contact.mail_template_kyc_expired_action_required',
            raise_if_not_found=False,
        )
        notified_ids = []
        if template:
            for partner in expired_partners:
                try:
                    template.send_mail(partner.id, force_send=True,)
                    notified_ids.append(partner.id)
                except Exception as e:
                    _logger.warning(
                        "RE-KYC Follow Up: Failed to send KYC expired email to partner %s (%s): %s",
                        partner.id, partner.name, e,
                    )
            if notified_ids:
                _logger.info(
                    "RE-KYC Follow Up: KYC expired notification sent to %s contact(s): %s",
                    len(notified_ids),
                    [partner_model.browse(pid).name for pid in notified_ids],
                )
        else:
            _logger.warning("RE-KYC Follow Up: mail_template_kyc_expired_action_required not found.")
