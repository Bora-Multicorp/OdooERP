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
    has_expired_docs = fields.Boolean(compute='_compute_has_expired_docs',
                                      help="True when any overseas KYC document expiry date has passed.")

    @api.depends('deadline')
    def _compute_is_expired(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_expired = bool(rec.deadline and rec.deadline <= today)

    @api.depends(
        'kyc_details.company_reg_doc_expiry',
        'kyc_details.authorized_person_id_expiry',
        'kyc_details.directors_detail.govt_id_expiry',
    )
    def _compute_has_expired_docs(self):
        today = fields.Date.context_today(self)
        for rec in self:
            kyc = rec.kyc_details.filtered(lambda k: k.state == 'confirmed')[:1]
            if not kyc:
                rec.has_expired_docs = False
                continue
            expired = (
                (kyc.company_reg_doc_expiry and kyc.company_reg_doc_expiry <= today)
                or (kyc.authorized_person_id_expiry and kyc.authorized_person_id_expiry <= today)
                or any(d.govt_id_expiry and d.govt_id_expiry <= today
                       for d in kyc.directors_detail)
            )
            rec.has_expired_docs = bool(expired)

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

    # @api.constrains('l10n_in_pan')
    # def _check_pan_card_no_format(self):
    #     """
    #     Validate Indian PAN number format and enforce uniqueness.
    #
    #     PAN Format:
    #         - 5 uppercase letters
    #         - 4 digits
    #         - 1 uppercase letter
    #         Example: ABCDE1234F
    #
    #     Raises
    #     ------
    #     ValidationError:
    #         If PAN format is invalid or duplicate PAN is found.
    #     """
    #     pan_regex = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
    #
    #     for rec in self:
    #         pan = (rec.l10n_in_pan or "").upper()
    #
    #         # Skip empty PAN
    #         if not pan:
    #             continue
    #
    #         # Validate PAN format
    #         if not pan_regex.match(pan):
    #             raise ValidationError(
    #                 _("Invalid PAN format: %s. Expected format: ABCDE1234F.") % rec.l10n_in_pan
    #             )
    #
    #         # Validate uniqueness (case-insensitive)
    #         duplicate = self.search([
    #             ('l10n_in_pan', '=ilike', pan),
    #             ('id', '!=', rec.id)
    #         ], limit=1)
    #
    #         if duplicate:
    #             raise ValidationError(
    #                 _("PAN number '%s' is already assigned to another contact.") % rec.l10n_in_pan
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
            if not rec.vat or rec.parent_id:
                continue

            gst = rec.vat.upper()

            if not gst_pattern.match(gst):
                raise ValidationError(_(
                    "Invalid GST Number: '%s'. It must follow the 15-character format (e.g., 27ABCDE1234F1Z5)."
                ) % rec.vat)

            duplicate = self.search([
                ('vat', '=ilike', gst),
                ('id', '!=', rec.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    _("GST number '%s' is already assigned to another contact.") % rec.vat
                )

    @api.constrains('phone', 'mobile', 'country_id')
    def _check_phone_mobile_format(self):
        for rec in self:
            # Check both fields: mobile and phone
            for field_name in ['mobile', 'phone']:
                value = getattr(rec, field_name)

                if not value:
                    continue

                # 1) First check country is added or not
                if not rec.country_id or not rec.country_id.phone_code:
                    raise ValidationError(
                        _("Please select a Country before entering the %s number so we can verify the format.") % field_name
                    )

                # 2) Strip non-digits (like +, -, spaces)
                cleaned_number = re.sub(r'\D', '', value)

                # 3) Remove leading country code
                code = str(rec.country_id.phone_code)
                if cleaned_number.startswith(code):
                    cleaned_number = cleaned_number[len(code):]
                elif cleaned_number.startswith('0') and len(cleaned_number) > 10:
                    # Handle leading zeros
                    cleaned_number = cleaned_number[1:]

                # 4) Validate exactly 10 digits
                if not re.fullmatch(r'\d{10}', cleaned_number):
                    raise ValidationError(
                        _("The %s number must be exactly 10 digits after removing the country code (+%s). "
                          "Currently, it is %s digits.") % (field_name, code, len(cleaned_number))
                    )

    # @api.constrains('phone', 'country_id')
    # def _check_phone_number_format(self):
    #     for rec in self:
    #         if not rec.phone:
    #             continue
    #
    #         # 1) Remove all non-digits
    #         cleaned_number = re.sub(r'\D', '', rec.phone)
    #
    #         # 2) Remove country code if present
    #         if rec.country_id and rec.country_id.phone_code:
    #             code = str(rec.country_id.phone_code)
    #             if code and cleaned_number.startswith(code):
    #                 cleaned_number = cleaned_number[len(code):]
    #
    #         # 3) Validate exactly 10 digits
    #         if not re.fullmatch(r'\d{10}', cleaned_number):
    #             raise ValidationError(
    #                 _("Phone number must be exactly 10 digits after removing the country code.")
    #             )

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
    is_overseas = fields.Boolean(
        string="Overseas Customer",
        default=False,
        tracking=True,
        help="Enable to apply KYC compliance checks for this overseas customer. "
             "Incomplete KYC will show a warning (non-blocking) on Sales Orders.",
    )
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
    rekyc_survey_url = fields.Char(
        string='Re-KYC Survey URL',
        help='Pre-filled survey link sent to vendor in KYC expiry email.',
    )

    def _compute_kyc_record_url(self):
        base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        for rec in self:
            rec.kyc_record_url = f"{base}/web#id={rec.id}&model=res.partner&view_type=form" if base else ''

    def _is_overseas_kyc_incomplete(self):
        """
        Returns True if this partner is overseas (vendor, customer, or both)
        and their KYC is not yet approved.
        """
        self.ensure_one()
        if not self.is_overseas:
            return False
        if self.customer_rank <= 0 and self.supplier_rank <= 0:
            return False
        return not self.is_approved

    def _get_rekyc_survey_url(self):
        """
        Create (or reuse) a survey.user_input for this partner pre-filled with
        ALL existing confirmed KYC data (simple fields + bank/director/address
        matrices), and return the unique start URL.
        """
        self.ensure_one()
        survey = self.env.ref('ks_contact.vendor_kyc_form_survey', raise_if_not_found=False)
        if not survey:
            return ''
        base_url = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')

        # Reuse existing 'in_progress' input or create a fresh one.
        # We set state='in_progress' immediately so the vendor lands directly on
        # the first question with pre-filled data visible (state='new' shows only
        # the start page and pre-filled lines are not rendered until in_progress).
        # No partner_id to avoid _check_validity partner-mismatch for public vendors.
        user_input = self.env['survey.user_input'].sudo().search([
            ('survey_id', '=', survey.id),
            ('email', '=', self.email),
            ('state', '=', 'in_progress'),
        ], limit=1)
        if not user_input:
            user_input = self.env['survey.user_input'].sudo().create({
                'survey_id': survey.id,
                'email': self.email or '',
                'state': 'in_progress',
                'start_datetime': fields.Datetime.now(),
            })

        # Remove any stale skipped=True lines left from previous save attempts.
        # These cause server-side "This question requires an answer" errors even
        # when pre-filled non-skipped lines exist for the same question.
        self.env['survey.user_input.line'].sudo().search([
            ('user_input_id', '=', user_input.id),
            ('skipped', '=', True),
        ]).unlink()

        # Pre-fill from the latest confirmed KYC record
        kyc = self.kyc_details.filtered(lambda k: k.state == 'confirmed')[:1]
        if not kyc:
            return '%s%s' % (base_url, user_input.get_start_url())

        Line = self.env['survey.user_input.line'].sudo()

        def _q(xml_id):
            return self.env.ref(xml_id, raise_if_not_found=False)

        def _upsert(q, vals):
            """Create or update a single user_input_line for a simple question."""
            if not q:
                return
            line = Line.search([
                ('user_input_id', '=', user_input.id),
                ('question_id', '=', q.id),
            ], limit=1)
            if line:
                line.write(vals)
            else:
                Line.create({'user_input_id': user_input.id, 'question_id': q.id,
                             'survey_id': survey.id, **vals})

        def _char(xml_id, value):
            if not value:
                return
            _upsert(_q(xml_id), {'answer_type': 'char_box', 'value_char_box': value, 'skipped': False})

        def _choice(xml_id, value):
            if not value:
                return
            q = _q(xml_id)
            if not q:
                return
            suggested = q.suggested_answer_ids.filtered(lambda a: a.value == value)[:1]
            if suggested:
                _upsert(q, {'answer_type': 'suggestion', 'suggested_answer_id': suggested.id, 'skipped': False})

        def _matrix_char(q, col_answer, row_answer, value):
            """Upsert one cell of a sh_custom_matrix as char_box.

            sh_custom_matrix_template renders 'textbox' columns via
            answer.value_text_box and 'free_text' columns via answer.value_char_box.
            We write both to stay safe; answer_type='char_box' satisfies the
            sh_survey_matrix_adv constraint (skipped==bool(answer_type) must be False).
            """
            if not value or not q or not col_answer or not row_answer:
                return
            line = Line.search([
                ('user_input_id', '=', user_input.id),
                ('question_id', '=', q.id),
                ('suggested_answer_id', '=', col_answer.id),
                ('matrix_row_id', '=', row_answer.id),
            ], limit=1)
            vals = {
                'answer_type': 'char_box',
                'value_char_box': value,
                'value_text_box': value,   # textbox columns read this field
                'skipped': False,
                'suggested_answer_id': col_answer.id,
                'matrix_row_id': row_answer.id,
            }
            if line:
                line.write(vals)
            else:
                Line.create({'user_input_id': user_input.id, 'question_id': q.id,
                             'survey_id': survey.id, **vals})

        def _matrix_m2o(q, col_answer, row_answer, record_id, record_name):
            """Upsert one cell of a sh_custom_matrix as ans_sh_many2one (stored as char name)."""
            if not record_id or not q or not col_answer or not row_answer:
                return
            line = Line.search([
                ('user_input_id', '=', user_input.id),
                ('question_id', '=', q.id),
                ('suggested_answer_id', '=', col_answer.id),
                ('matrix_row_id', '=', row_answer.id),
            ], limit=1)
            vals = {'answer_type': 'ans_sh_many2one', 'value_ans_sh_many2one': str(record_name),
                    'skipped': False, 'suggested_answer_id': col_answer.id, 'matrix_row_id': row_answer.id}
            if line:
                line.write(vals)
            else:
                Line.create({'user_input_id': user_input.id, 'question_id': q.id,
                             'survey_id': survey.id, **vals})

        def _file_from_attachment(xml_id, attachment):
            """Create one user_input_line for a single ir.attachment (file question)."""
            if not attachment:
                return
            q = _q(xml_id)
            if not q:
                return
            # Read binary data; use sudo for ir.attachment, direct access for plain objects
            try:
                att_sudo = attachment.sudo() if hasattr(attachment, '_name') else attachment
                data = att_sudo.datas
                name = att_sudo.name
            except Exception:
                return
            if not data:
                return
            Line.search([('user_input_id', '=', user_input.id),
                         ('question_id', '=', q.id)]).unlink()
            Line.create({
                'user_input_id': user_input.id,
                'question_id': q.id,
                'survey_id': survey.id,
                'answer_type': 'ans_sh_file',
                'value_ans_sh_file': data,
                'value_ans_sh_file_fname': name,
                'skipped': False,
            })

        def _files_from_m2m(xml_id, attachments):
            """Create one user_input_line per attachment for a many2many file question."""
            if not attachments:
                _logger.info("REKYC_PREFILL [%s] no attachments, skipping", xml_id)
                return
            q = _q(xml_id)
            if not q:
                _logger.warning("REKYC_PREFILL [%s] question not found", xml_id)
                return
            Line.search([('user_input_id', '=', user_input.id),
                         ('question_id', '=', q.id)]).unlink()
            created = 0
            for att in attachments.sudo():
                try:
                    data = att.datas
                    fname = att.name
                except Exception as e:
                    _logger.warning("REKYC_PREFILL [%s] att %s read error: %s", xml_id, att.id, e)
                    continue
                if not data:
                    _logger.warning("REKYC_PREFILL [%s] att %s has no data (datas=False)", xml_id, att.id)
                    continue
                try:
                    Line.create({
                        'user_input_id': user_input.id,
                        'question_id': q.id,
                        'survey_id': survey.id,
                        'answer_type': 'ans_sh_file',
                        'value_ans_sh_file': data,
                        'value_ans_sh_file_fname': fname,
                        'skipped': False,
                    })
                    created += 1
                except Exception as e:
                    _logger.warning("REKYC_PREFILL [%s] line create failed: %s", xml_id, e)
            _logger.info("REKYC_PREFILL [%s] created %d file lines from %d attachments",
                         xml_id, created, len(attachments))

        def _matrix_file(q, col_answer, row_answer, attachment):
            """Upsert one file cell of a sh_custom_matrix from an ir.attachment."""
            if not attachment or not q or not col_answer or not row_answer:
                return
            # Support both ir.attachment records and simple objects with .datas/.name
            att_sudo = attachment.sudo() if hasattr(attachment, 'sudo') else attachment
            try:
                data = att_sudo.datas
                fname = att_sudo.name
            except Exception:
                return
            if not data:
                return
            Line.search([
                ('user_input_id', '=', user_input.id),
                ('question_id', '=', q.id),
                ('suggested_answer_id', '=', col_answer.id),
                ('matrix_row_id', '=', row_answer.id),
            ]).unlink()
            Line.create({
                'user_input_id': user_input.id,
                'question_id': q.id,
                'survey_id': survey.id,
                'answer_type': 'ans_sh_file',
                'value_ans_sh_file': data,
                'value_ans_sh_file_fname': fname,
                'skipped': False,
                'suggested_answer_id': col_answer.id,
                'matrix_row_id': row_answer.id,
            })

        # ── Simple char fields ──────────────────────────────────────────────
        _char('ks_contact.email_kyc_survey',               kyc.email)
        _char('ks_contact.point_of_contact_kyc_survey',    kyc.point_of_contact)
        _char('ks_contact.business_name_kyc_survey',       kyc.business_legal_name)
        _char('ks_contact.business_trade_name_kyc_survey', kyc.business_trade_name)
        _char('ks_contact.gst_no_kyc_survey',              kyc.gst_no)
        _char('ks_contact.pan_card_no_kyc_survey',         kyc.pan_no)
        _char('ks_contact.udyam_certificate_kyc_survey',   kyc.udyam_number)
        _char('ks_contact.cin_no_kyc_survey',              kyc.cin_no)
        _char('ks_contact.registration_kyc_survey',        kyc.license_registered)
        _char('ks_contact.comp_google_loc_kyc_survey',     kyc.comp_google_loc)
        _char('ks_contact.partnership_llp_kyc_survey',     kyc.partner_llp)

        # ── Selection / choice fields ───────────────────────────────────────
        _choice('ks_contact.is_same_trade_name_kyc_survey',    kyc.is_same_trade_name)
        _choice('ks_contact.business_constitution_kyc_survey', kyc.const_business)
        _choice('ks_contact.aadhaar_pan_link_kyc_survey',      kyc.aadhaar_pan_link)
        _choice('ks_contact.gst_duration_kyc_survey',          kyc.gst_return_duration)
        _choice('ks_contact.no_of_director_kyc_survey',        kyc.no_partner_director)

        # ── Document / file fields (many2many → one line per attachment) ────
        _files_from_m2m('ks_contact.gst_certificate_kyc_survey',         kyc.gst_certificate)
        _files_from_m2m('ks_contact.shop_act_document_kyc_survey',       kyc.shop_act_document)
        _files_from_m2m('ks_contact.udyam_document_kyc_survey',          kyc.udyam_document)
        _files_from_m2m('ks_contact.pan_card_document_kyc_survey',       kyc.pan_card_document)
        _files_from_m2m('ks_contact.shop_photos_kyc_survey',             kyc.shop_photos)
        _files_from_m2m('ks_contact.shop_videos_kyc_survey',             kyc.shop_videos)
        _files_from_m2m('ks_contact.electricity_bill_kyc_survey',        kyc.electricity_bill)
        _files_from_m2m('ks_contact.incorporation_certificate_kyc_survey', kyc.incorporation_certificate)
        _files_from_m2m('ks_contact.moa_aoa_kyc_survey',                 kyc.moa_aoa)
        # partner_llp is Binary (not many2many) — wrap in a single file line
        if kyc.partner_llp:
            # Create a temporary attachment-like object from the binary field
            _file_from_attachment(
                'ks_contact.partnership_llp_kyc_survey',
                type('_att', (), {'datas': kyc.partner_llp, 'name': 'partnership_llp.pdf'})()
            )

        # ── BANK DETAILS matrix ─────────────────────────────────────────────
        # Columns: col1=Bank Name, col2=Account Number, col3=IFSC Code,
        #          col4=Bank Address, col5=Cancelled Cheque (file)
        q_bank = _q('ks_contact.matrix_bank_address_kyc_survey')
        if q_bank and kyc.bank_detail:
            col_bank_name    = self.env.ref('ks_contact.matrix_bank_address_kyc_survey_col1', False)
            col_account_no   = self.env.ref('ks_contact.matrix_bank_address_kyc_survey_col2', False)
            col_ifsc         = self.env.ref('ks_contact.matrix_bank_address_kyc_survey_col3', False)
            col_bank_address = self.env.ref('ks_contact.matrix_bank_address_kyc_survey_col4', False)
            col_cheque       = self.env.ref('ks_contact.matrix_bank_address_kyc_survey_col5', False)

            bank_rows = q_bank.matrix_row_ids.sorted('sequence')

            for idx, bank in enumerate(kyc.bank_detail):
                if idx >= len(bank_rows):
                    break
                row = bank_rows[idx]
                _matrix_char(q_bank, col_bank_name,    row, bank.bank_name)
                _matrix_char(q_bank, col_account_no,   row, bank.account_no)
                _matrix_char(q_bank, col_ifsc,         row, bank.ifsc_code)
                _matrix_char(q_bank, col_bank_address, row, bank.bank_address)
                # Cancelled Cheque — use first attachment if available
                cheque_att = bank.bank_cheque_attachments[:1]
                if cheque_att:
                    _matrix_file(q_bank, col_cheque, row, cheque_att)

        # ── DIRECTOR DETAILS matrix ─────────────────────────────────────────
        # Columns: col1=Designation, col2=Name, col3=Contact Number,
        #          col4=Email Address, col5=Aadhaar Card (file), col6=PAN Card (file)
        q_dir = _q('ks_contact.matrix_director_detail_kyc_survey')
        if q_dir and kyc.directors_detail:
            col_desig   = self.env.ref('ks_contact.matrix_director_detail_kyc_survey_col1', False)
            col_name    = self.env.ref('ks_contact.matrix_director_detail_kyc_survey_col2', False)
            col_contact = self.env.ref('ks_contact.matrix_director_detail_kyc_survey_col3', False)
            col_email   = self.env.ref('ks_contact.matrix_director_detail_kyc_survey_col4', False)
            col_aadhaar = self.env.ref('ks_contact.matrix_director_detail_kyc_survey_col5', False)
            col_pan     = self.env.ref('ks_contact.matrix_director_detail_kyc_survey_col6', False)

            dir_rows = q_dir.matrix_row_ids.sorted('sequence')

            for idx, director in enumerate(kyc.directors_detail):
                if idx >= len(dir_rows):
                    break
                row = dir_rows[idx]
                _matrix_char(q_dir, col_desig,   row, director.designation)
                _matrix_char(q_dir, col_name,    row, director.name)
                _matrix_char(q_dir, col_contact, row, director.contact_no)
                _matrix_char(q_dir, col_email,   row, director.email)
                # Aadhaar Card — use first attachment
                aadhaar_att = director.aadhaar_card_attachments[:1]
                if aadhaar_att:
                    _matrix_file(q_dir, col_aadhaar, row, aadhaar_att)
                # PAN Card — use first attachment
                pan_att = director.pan_card_attachments[:1]
                if pan_att:
                    _matrix_file(q_dir, col_pan, row, pan_att)

        # ── ADDRESS DETAILS matrix ──────────────────────────────────────────
        # Columns: col1=Address, col2=City Name, col3=Pincode, col4=Contact Number,
        #          col5=Email, col6=State (m2o), col7=Country (m2o)
        q_addr = _q('ks_contact.matrix_address_detail_kyc_survey')
        if q_addr and kyc.address_detail:
            col_addr    = self.env.ref('ks_contact.matrix_address_detail_kyc_survey_col1', False)
            col_city    = self.env.ref('ks_contact.matrix_address_detail_kyc_survey_col2', False)
            col_pin     = self.env.ref('ks_contact.matrix_address_detail_kyc_survey_col3', False)
            col_phone   = self.env.ref('ks_contact.matrix_address_detail_kyc_survey_col4', False)
            col_email   = self.env.ref('ks_contact.matrix_address_detail_kyc_survey_col5', False)
            col_state   = self.env.ref('ks_contact.matrix_address_detail_kyc_survey_col6', False)
            col_country = self.env.ref('ks_contact.matrix_address_detail_kyc_survey_col7', False)

            addr_rows = q_addr.matrix_row_ids.sorted('sequence')

            for idx, addr in enumerate(kyc.address_detail):
                if idx >= len(addr_rows):
                    break
                row = addr_rows[idx]
                _matrix_char(q_addr, col_addr,  row, addr.business_street)
                _matrix_char(q_addr, col_city,  row, addr.business_city)
                _matrix_char(q_addr, col_pin,   row, addr.business_pincode)
                _matrix_char(q_addr, col_phone, row, addr.business_phone)
                _matrix_char(q_addr, col_email, row, addr.business_email)
                if addr.business_state_id:
                    _matrix_m2o(q_addr, col_state, row,
                                addr.business_state_id.id, addr.business_state_id.name)
                if addr.business_country_id:
                    _matrix_m2o(q_addr, col_country, row,
                                addr.business_country_id.id, addr.business_country_id.name)

        return '%s%s' % (base_url, user_input.get_start_url())

    def _get_overseas_rekyc_survey_url(self):
        """
        Create (or reuse) a survey.user_input for this overseas partner pre-filled
        with ALL existing confirmed KYC data (simple fields + bank/director/address
        matrices) from the overseas KYC survey, and return the unique start URL.
        """
        self.ensure_one()
        survey = self.env.ref('ks_contact.overseas_kyc_form_survey', raise_if_not_found=False)
        if not survey:
            return ''
        base_url = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')

        user_input = self.env['survey.user_input'].sudo().search([
            ('survey_id', '=', survey.id),
            ('email', '=', self.email),
            ('state', '=', 'in_progress'),
        ], limit=1)
        if not user_input:
            user_input = self.env['survey.user_input'].sudo().create({
                'survey_id': survey.id,
                'email': self.email or '',
                'state': 'in_progress',
                'start_datetime': fields.Datetime.now(),
            })

        # Remove stale skipped=True lines from previous attempts
        self.env['survey.user_input.line'].sudo().search([
            ('user_input_id', '=', user_input.id),
            ('skipped', '=', True),
        ]).unlink()

        kyc = self.kyc_details.filtered(lambda k: k.state == 'confirmed')[:1]
        if not kyc:
            return '%s%s' % (base_url, user_input.get_start_url())

        Line = self.env['survey.user_input.line'].sudo()

        def _q(xml_id):
            return self.env.ref(xml_id, raise_if_not_found=False)

        def _upsert(q, vals):
            if not q:
                return
            line = Line.search([
                ('user_input_id', '=', user_input.id),
                ('question_id', '=', q.id),
            ], limit=1)
            if line:
                line.write(vals)
            else:
                Line.create({'user_input_id': user_input.id, 'question_id': q.id,
                             'survey_id': survey.id, **vals})

        def _char(xml_id, value):
            if not value:
                return
            _upsert(_q(xml_id), {'answer_type': 'char_box', 'value_char_box': value, 'skipped': False})

        def _choice(xml_id, value):
            if not value:
                return
            q = _q(xml_id)
            if not q:
                return
            suggested = q.suggested_answer_ids.filtered(lambda a: a.value == value)[:1]
            if suggested:
                _upsert(q, {'answer_type': 'suggestion', 'suggested_answer_id': suggested.id, 'skipped': False})

        def _matrix_char(q, col_answer, row_answer, value):
            if not value or not q or not col_answer or not row_answer:
                return
            line = Line.search([
                ('user_input_id', '=', user_input.id),
                ('question_id', '=', q.id),
                ('suggested_answer_id', '=', col_answer.id),
                ('matrix_row_id', '=', row_answer.id),
            ], limit=1)
            vals = {
                'answer_type': 'char_box',
                'value_char_box': value,
                'value_text_box': value,
                'skipped': False,
                'suggested_answer_id': col_answer.id,
                'matrix_row_id': row_answer.id,
            }
            if line:
                line.write(vals)
            else:
                Line.create({'user_input_id': user_input.id, 'question_id': q.id,
                             'survey_id': survey.id, **vals})

        def _matrix_m2o(q, col_answer, row_answer, record_id, record_name):
            if not record_id or not q or not col_answer or not row_answer:
                return
            line = Line.search([
                ('user_input_id', '=', user_input.id),
                ('question_id', '=', q.id),
                ('suggested_answer_id', '=', col_answer.id),
                ('matrix_row_id', '=', row_answer.id),
            ], limit=1)
            vals = {'answer_type': 'ans_sh_many2one', 'value_ans_sh_many2one': str(record_name),
                    'skipped': False, 'suggested_answer_id': col_answer.id, 'matrix_row_id': row_answer.id}
            if line:
                line.write(vals)
            else:
                Line.create({'user_input_id': user_input.id, 'question_id': q.id,
                             'survey_id': survey.id, **vals})

        def _matrix_file(q, col_answer, row_answer, attachment):
            if not attachment or not q or not col_answer or not row_answer:
                return
            att_sudo = attachment.sudo() if hasattr(attachment, 'sudo') else attachment
            try:
                data = att_sudo.datas
                fname = att_sudo.name
            except Exception:
                return
            if not data:
                return
            Line.search([
                ('user_input_id', '=', user_input.id),
                ('question_id', '=', q.id),
                ('suggested_answer_id', '=', col_answer.id),
                ('matrix_row_id', '=', row_answer.id),
            ]).unlink()
            Line.create({
                'user_input_id': user_input.id,
                'question_id': q.id,
                'survey_id': survey.id,
                'answer_type': 'ans_sh_file',
                'value_ans_sh_file': data,
                'value_ans_sh_file_fname': fname,
                'skipped': False,
                'suggested_answer_id': col_answer.id,
                'matrix_row_id': row_answer.id,
            })

        def _files_from_m2m(xml_id, attachments):
            if not attachments:
                return
            q = _q(xml_id)
            if not q:
                return
            Line.search([('user_input_id', '=', user_input.id), ('question_id', '=', q.id)]).unlink()
            for att in attachments.sudo():
                try:
                    data = att.datas
                    fname = att.name
                except Exception:
                    continue
                if not data:
                    continue
                Line.create({
                    'user_input_id': user_input.id,
                    'question_id': q.id,
                    'survey_id': survey.id,
                    'answer_type': 'ans_sh_file',
                    'value_ans_sh_file': data,
                    'value_ans_sh_file_fname': fname,
                    'skipped': False,
                })

        def _date(xml_id, value):
            """Pre-fill a standard date question with an existing date value."""
            if not value:
                return
            _upsert(_q(xml_id), {'answer_type': 'date', 'value_date': value, 'skipped': False})

        def _matrix_date(q, col_answer, row_answer, value):
            """Pre-fill a matrix date cell."""
            if not value or not q or not col_answer or not row_answer:
                return
            line = Line.search([
                ('user_input_id', '=', user_input.id),
                ('question_id', '=', q.id),
                ('suggested_answer_id', '=', col_answer.id),
                ('matrix_row_id', '=', row_answer.id),
            ], limit=1)
            vals = {
                'answer_type': 'date',
                'value_date': value,
                'skipped': False,
                'suggested_answer_id': col_answer.id,
                'matrix_row_id': row_answer.id,
            }
            if line:
                line.write(vals)
            else:
                Line.create({'user_input_id': user_input.id, 'question_id': q.id,
                             'survey_id': survey.id, **vals})

        # ── Simple char fields ──────────────────────────────────────────────
        _char('ks_contact.overseas_email_kyc_survey',          kyc.email)
        _char('ks_contact.overseas_poc_kyc_survey',            kyc.point_of_contact)
        _char('ks_contact.overseas_business_name_kyc_survey',  kyc.business_legal_name)
        _char('ks_contact.overseas_trade_name_kyc_survey',     kyc.business_trade_name)

        # ── Selection / choice fields ───────────────────────────────────────
        _choice('ks_contact.overseas_same_trade_name_kyc_survey',  'Yes' if kyc.is_same_trade_name else '')
        _choice('ks_contact.overseas_const_business_kyc_survey',   kyc.const_business)
        _choice('ks_contact.overseas_no_directors_kyc_survey',     kyc.no_partner_director)

        # ── POC (que_sh_many2one) — no static suggested_answer_ids; store as ans_sh_many2one ───
        if kyc.poc_user:
            q_poc = _q('ks_contact.overseas_company_poc_kyc_survey')
            if q_poc:
                _upsert(q_poc, {'answer_type': 'ans_sh_many2one',
                                'value_ans_sh_many2one': kyc.poc_user.name,
                                'skipped': False})

        # ── Document files ──────────────────────────────────────────────────
        _files_from_m2m('ks_contact.overseas_company_reg_doc_kyc_survey',
                        kyc.company_reg_document)
        _date('ks_contact.overseas_company_reg_doc_expiry_survey', kyc.company_reg_doc_expiry)
        _files_from_m2m('ks_contact.overseas_auth_person_id_doc_kyc_survey',
                        kyc.authorized_person_id_document)
        _date('ks_contact.overseas_auth_person_id_expiry_survey', kyc.authorized_person_id_expiry)

        # ── BANK DETAILS matrix ─────────────────────────────────────────────
        q_bank = _q('ks_contact.overseas_matrix_bank_kyc_survey')
        if q_bank and kyc.bank_detail:
            col_bank_name  = self.env.ref('ks_contact.overseas_bank_col_name',    False)
            col_account_no = self.env.ref('ks_contact.overseas_bank_col_account', False)
            col_swift      = self.env.ref('ks_contact.overseas_bank_col_swift',   False)
            col_cheque     = self.env.ref('ks_contact.overseas_bank_col_cheque',  False)

            bank_rows = q_bank.matrix_row_ids.sorted('sequence')
            for idx, bank in enumerate(kyc.bank_detail):
                if idx >= len(bank_rows):
                    break
                row = bank_rows[idx]
                _matrix_char(q_bank, col_bank_name,  row, bank.bank_name)
                _matrix_char(q_bank, col_account_no, row, bank.account_no)
                _matrix_char(q_bank, col_swift,      row, bank.ifsc_code)
                cheque_att = bank.bank_cheque_attachments[:1]
                if cheque_att:
                    _matrix_file(q_bank, col_cheque, row, cheque_att)

        # ── DIRECTOR DETAILS matrix ─────────────────────────────────────────
        q_dir = _q('ks_contact.overseas_matrix_director_kyc_survey')
        if q_dir and kyc.directors_detail:
            col_desig      = self.env.ref('ks_contact.overseas_dir_col_designation',  False)
            col_name       = self.env.ref('ks_contact.overseas_dir_col_name',         False)
            col_contact    = self.env.ref('ks_contact.overseas_dir_col_contact',      False)
            col_email      = self.env.ref('ks_contact.overseas_dir_col_email',        False)
            col_govt_id    = self.env.ref('ks_contact.overseas_dir_col_govt_id',      False)
            col_id_expiry  = self.env.ref('ks_contact.overseas_dir_col_govt_id_expiry', False)

            dir_rows = q_dir.matrix_row_ids.sorted('sequence')
            for idx, director in enumerate(kyc.directors_detail):
                if idx >= len(dir_rows):
                    break
                row = dir_rows[idx]
                _matrix_char(q_dir, col_desig,   row, director.designation)
                _matrix_char(q_dir, col_name,    row, director.name)
                _matrix_char(q_dir, col_contact, row, director.contact_no)
                _matrix_char(q_dir, col_email,   row, director.email)
                govt_id_att = director.govt_id_attachments[:1]
                if govt_id_att:
                    _matrix_file(q_dir, col_govt_id, row, govt_id_att)
                if director.govt_id_expiry:
                    _matrix_date(q_dir, col_id_expiry, row, director.govt_id_expiry)

        # ── ADDRESS DETAILS matrix ──────────────────────────────────────────
        # State is free-text for overseas; Country is many2one
        q_addr = _q('ks_contact.overseas_matrix_address_kyc_survey')
        if q_addr and kyc.address_detail:
            col_addr    = self.env.ref('ks_contact.overseas_addr_col_street',  False)
            col_city    = self.env.ref('ks_contact.overseas_addr_col_city',    False)
            col_pin     = self.env.ref('ks_contact.overseas_addr_col_pincode', False)
            col_phone   = self.env.ref('ks_contact.overseas_addr_col_phone',   False)
            col_email   = self.env.ref('ks_contact.overseas_addr_col_email',   False)
            col_state   = self.env.ref('ks_contact.overseas_addr_col_state',   False)
            col_country = self.env.ref('ks_contact.overseas_addr_col_country', False)

            addr_rows = q_addr.matrix_row_ids.sorted('sequence')
            for idx, addr in enumerate(kyc.address_detail):
                if idx >= len(addr_rows):
                    break
                row = addr_rows[idx]
                _matrix_char(q_addr, col_addr,  row, addr.business_street)
                _matrix_char(q_addr, col_city,  row, addr.business_city)
                _matrix_char(q_addr, col_pin,   row, addr.business_pincode)
                _matrix_char(q_addr, col_phone, row, addr.business_phone)
                _matrix_char(q_addr, col_email, row, addr.business_email)
                # State is textbox for overseas (not m2o)
                state_text = addr.business_state_id.name if addr.business_state_id else ''
                _matrix_char(q_addr, col_state, row, state_text)
                if addr.business_country_id:
                    _matrix_m2o(q_addr, col_country, row,
                                addr.business_country_id.id, addr.business_country_id.name)

        return '%s%s' % (base_url, user_input.get_start_url())

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

    ks_is_approver = fields.Boolean(
        string='Is Approver',
        compute='_compute_ks_is_approver',
        help='True if current user is any approver on this vendor approval.',
    )

    @api.depends('approval_line_ids.user_id', 'approval_line_ids.is_active')
    @api.depends_context('uid')
    def _compute_ks_is_approver(self):
        uid = self.env.uid
        for record in self:
            record.ks_is_approver = uid in record.approval_line_ids.filtered('is_active').mapped('user_id').ids

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

    def _ks_cancel_pending_partner_approval_activities(self, mark_done=False, feedback=None):
        """Cancel pending vendor-approval activities on this partner.

        Scoped by: res_model + res_id + user_ids of active approval_line_ids
        + summary keyword — so only vendor-approval activities are touched.

        :param mark_done: True  → action_feedback (leaves chatter entry)
                          False → unlink (silent, used for 'Update' resets)
        """
        self.ensure_one()
        approver_user_ids = self.approval_line_ids.filtered('is_active').mapped('user_id').ids
        domain = [
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('active', '=', True),
            ('summary', 'ilike', 'Vendor Approval'),
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
        """Submitter/admin updates vendor approvers while approval_status is 'to_approve'.

        Only opens the wizard with ks_is_update=True — ALL cleanup (cancel activities,
        clear approval_line_ids) happens inside the wizard's add_users_for_approval
        ONLY when the user clicks OK.  Clicking wizard Cancel leaves everything untouched.
        """
        self.ensure_one()
        if self.approval_status != 'to_approve':
            raise ValidationError(_("Update Approvals is only available while the vendor is in 'To Approve' state."))

        current_user = self.env.user
        is_admin = current_user.has_group('base.group_system')
        # Any internal user who can see the button is allowed (admins + managers)
        if not is_admin and not current_user.has_group('base.group_user'):
            raise ValidationError(_("You do not have permission to update approval requests."))

        config = self.env['vendor.approval.config'].get_config()
        if not config:
            raise ValidationError(_("Please configure Vendor Approval Settings before updating."))

        return {
            'name': _('Update Approval Users'),
            'type': 'ir.actions.act_window',
            'res_model': 'partner.approval.user.picker.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'ks_is_update': True,
                'default_ks_is_update_mode': True,
                'default_approver1_user': self.approval_line_ids.filtered(lambda l: l.sequence == 1)[:1].user_id.id or False,
                'default_approver2_user': self.approval_line_ids.filtered(lambda l: l.sequence == 2)[:1].user_id.id or False,
            },
        }

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
            ('deadline', '<=', today),
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
                    # Generate pre-filled survey URL and persist it so the
                    # email template can read it as object.rekyc_survey_url
                    if partner.is_overseas:
                        survey_url = partner._get_overseas_rekyc_survey_url()
                    else:
                        survey_url = partner._get_rekyc_survey_url()
                    partner.sudo().write({'rekyc_survey_url': survey_url})
                    template.send_mail(partner.id)
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

        # 3️⃣ Document-level expiry tracking for overseas partners
        # Trigger re-KYC when any document has expired or is expiring within 30 days.
        self._check_overseas_doc_expiry(today, template, partner_model, activity_model, partner_model_id, activity_type, notified_ids)

    @api.model
    def _check_overseas_doc_expiry(self, today, template, partner_model, activity_model, partner_model_id, activity_type, already_notified_ids):
        """
        Check overseas KYC document expiry dates and:
        - Create follow-up activity when any document expires within 30 days.
        - Trigger re-KYC email when any document has expired (and partner not already notified).
        """
        from dateutil.relativedelta import relativedelta as _rd
        warning_date = today + _rd(days=30)

        KycModel = self.env['res.partner.kyc.approval']
        DirectorModel = self.env['director.details']

        # Collect overseas KYC records with expiring/expired documents
        expiring_kycs = KycModel.search([
            ('is_overseas', '=', True),
            ('state', '=', 'confirmed'),
            '|',
            ('company_reg_doc_expiry', '!=', False),
            ('authorized_person_id_expiry', '!=', False),
        ])

        # Also gather KYC IDs from director records with expiring govt IDs
        expiring_director_kyc_ids = DirectorModel.search([
            ('govt_id_expiry', '!=', False),
            ('kyc_approval_id.state', '=', 'confirmed'),
            ('kyc_approval_id.is_overseas', '=', True),
        ]).mapped('kyc_approval_id').ids

        kyc_records = expiring_kycs | KycModel.browse(expiring_director_kyc_ids)

        for kyc in kyc_records:
            partner = kyc.partner_id
            if not partner or not partner.email:
                continue

            # Collect all document expiry dates for this KYC
            doc_expiries = []
            if kyc.company_reg_doc_expiry:
                doc_expiries.append(('Trade License / Company Reg.', kyc.company_reg_doc_expiry))
            if kyc.authorized_person_id_expiry:
                doc_expiries.append(('Authorized Person ID', kyc.authorized_person_id_expiry))
            for director in kyc.directors_detail:
                if director.govt_id_expiry:
                    doc_expiries.append(
                        (f"Govt. ID ({director.name or 'Director'})", director.govt_id_expiry)
                    )

            if not doc_expiries:
                continue

            expired_docs = [(label, exp) for label, exp in doc_expiries if exp <= today]
            warning_docs = [(label, exp) for label, exp in doc_expiries if today < exp <= warning_date]

            # Activity for documents expiring within 30 days (not yet expired)
            if warning_docs:
                doc_list = ', '.join(f"{label} (expires {exp})" for label, exp in warning_docs)
                summary = 'Document Expiry Warning'
                existing_activity = activity_model.search([
                    ('res_model_id', '=', partner_model_id),
                    ('res_id', '=', partner.id),
                    ('summary', '=', summary),
                ], limit=1)
                if not existing_activity:
                    activity_model.create({
                        'activity_type_id': activity_type.id,
                        'summary': summary,
                        'note': f'Document(s) expiring soon for {partner.name}: {doc_list}',
                        'date_deadline': min(exp for _, exp in warning_docs),
                        'user_id': partner.user_id.id or self.env.user.id,
                        'res_model_id': partner_model_id,
                        'res_id': partner.id,
                    })

            # Re-KYC email for expired documents (skip if already notified via main deadline)
            if expired_docs and partner.id not in already_notified_ids and template:
                try:
                    if partner.is_overseas:
                        survey_url = partner._get_overseas_rekyc_survey_url()
                    else:
                        survey_url = partner._get_rekyc_survey_url()
                    partner.sudo().write({'rekyc_survey_url': survey_url})
                    template.send_mail(partner.id)
                    already_notified_ids.append(partner.id)
                    _logger.info(
                        "RE-KYC Follow Up: Document expiry re-KYC email sent to %s (%s). Expired docs: %s",
                        partner.id, partner.name,
                        [label for label, _ in expired_docs],
                    )
                except Exception as e:
                    _logger.warning(
                        "RE-KYC Follow Up: Failed to send doc-expiry re-KYC email to %s (%s): %s",
                        partner.id, partner.name, e,
                    )
