# -*- coding: utf-8 -*-
import logging
from odoo import models,fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    kyc_error_message = fields.Char(
        string="KYC Processing Error",
        help="Stores any error that occurred while creating the KYC record from this survey response.",
        readonly=True,
    )

    def _get_skipped_questions(self):
        result = super()._get_skipped_questions()
        if not result:
            return result
        has_file_data_q_ids = self.user_input_line_ids.filtered(
            lambda l: l.question_id.question_type == 'que_sh_file' and l.value_ans_sh_file
        ).mapped('question_id')
        return result - has_file_data_q_ids

    def save_line_que_sh_file(self, question, old_answers, answer, answer_type):
        file_list = answer if isinstance(answer, list) else ([answer] if isinstance(answer, dict) else [])
        has_new_file = any(isinstance(f, dict) and f.get('datas') for f in file_list)
        if not has_new_file:
            existing = self.env['survey.user_input.line'].sudo().search([
                ('user_input_id', '=', self.id),
                ('question_id', '=', question.id),
                ('answer_type', '=', 'ans_sh_file'),
                ('value_ans_sh_file', '!=', False),
            ])
            if existing:
                self.env['survey.user_input.line'].sudo().search([
                    ('user_input_id', '=', self.id),
                    ('question_id', '=', question.id),
                    ('skipped', '=', True),
                ]).unlink()
                return existing
        return super().save_line_que_sh_file(question, old_answers, answer, answer_type)

    def _save_line_matrix(self, question, old_answers, answers, comment):
        """
        Override: preserve pre-filled ans_sh_file lines for matrix cells where no
        new file was uploaded. The parent (sh_survey_matrix_adv) calls
        old_answers.sudo().unlink() unconditionally, which destroys pre-filled
        binary data when the vendor doesn't re-upload the file.
        """
        if question.matrix_subtype != 'sh_custom_matrix':
            return super()._save_line_matrix(question, old_answers, answers, comment)

        # Capture existing file cell data BEFORE super() unlinks them
        existing_files = {}
        for line in old_answers:
            if line.answer_type == 'ans_sh_file' and line.value_ans_sh_file:
                key = (line.suggested_answer_id.id, line.matrix_row_id.id)
                existing_files[key] = {
                    'data': line.value_ans_sh_file,
                    'fname': line.value_ans_sh_file_fname,
                    'col_id': line.suggested_answer_id.id,
                    'row_id': line.matrix_row_id.id,
                }

        result = super()._save_line_matrix(question, old_answers, answers, comment)

        if not existing_files:
            return result

        # Re-create file lines for cells where no new file was submitted by the vendor
        for (col_id, row_id), file_info in existing_files.items():
            new_for_cell = result.filtered(
                lambda l, c=col_id, r=row_id: (
                    l.suggested_answer_id.id == c
                    and l.matrix_row_id.id == r
                    and l.answer_type == 'ans_sh_file'
                )
            )
            if not new_for_cell:
                self.env['survey.user_input.line'].sudo().create({
                    'user_input_id': self.id,
                    'question_id': question.id,
                    'survey_id': question.survey_id.id,
                    'answer_type': 'ans_sh_file',
                    'value_ans_sh_file': file_info['data'],
                    'value_ans_sh_file_fname': file_info['fname'],
                    'skipped': False,
                    'suggested_answer_id': col_id,
                    'matrix_row_id': row_id,
                })

        return result

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _find_partner_by_email(self, email, overseas=False):
        if not email:
            return self.env['res.partner'].browse()
        if overseas:
            # Overseas partners can be vendors, customers, or both — match on is_overseas only
            return self.env['res.partner'].sudo().search([
                ('email', '=ilike', email),
                ('is_overseas', '=', True),
            ], limit=1)
        # Indian vendor survey: match vendor first, then fall back to overseas
        partner = self.env['res.partner'].sudo().search([
            ('email', '=ilike', email),
            ('is_vendor', '=', True),
        ], limit=1)
        if partner:
            return partner
        return self.env['res.partner'].sudo().search([
            ('email', '=ilike', email),
            ('is_overseas', '=', True),
        ], limit=1)

    def _get_email_from_lines(self, email_question_xmlid):
        """Read submitted email from the survey answer lines (fallback when self.email is empty)."""
        q = self.env.ref(email_question_xmlid, raise_if_not_found=False)
        if not q:
            return ''
        line = self.user_input_line_ids.filtered(lambda l: l.question_id == q)[:1]
        return (line.value_char_box or '').strip()

    def _create_attachment(self, fname, data):
        return self.env['ir.attachment'].sudo().create({
            'name': fname,
            'datas': data,
            'type': 'binary',
        }).id

    def _parse_file_line(self, line, field, field_name, attachments_by_field, values):
        file_data = line.value_ans_sh_file
        file_name = line.value_ans_sh_file_fname or f"file_{line.id}"
        if not file_data:
            return
        if isinstance(file_data, list):
            for entry in file_data:
                d = entry.get("datas") or entry.get("value")
                f = entry.get("filename") or file_name
                if not d:
                    continue
                if field.type == 'binary':
                    values[field_name] = d
                else:
                    attachments_by_field.setdefault(field_name, []).append(self._create_attachment(f, d))
        else:
            if field.type == 'binary':
                values[field_name] = file_data
            else:
                attachments_by_field.setdefault(field_name, []).append(self._create_attachment(file_name, file_data))

    def _build_matrix_maps(self, question):
        """Return (row_data_map, line_map) for a matrix question."""
        matrix_lines = self.user_input_line_ids.filtered(
            lambda l: l.question_id == question and l.matrix_row_id and l.answer_type
        )
        row_data_map = {}
        line_map = {}
        for ml in matrix_lines:
            row_id = ml.matrix_row_id.id
            col_name = (ml.suggested_answer_id.value or '').strip()
            if not col_name:
                continue
            val = getattr(ml, f"value_{ml.answer_type}", None)
            if isinstance(val, models.BaseModel):
                val = val.id
            row_data_map.setdefault(row_id, {})[col_name] = val
            line_map.setdefault(row_id, {})[col_name] = ml
        return row_data_map, line_map

    def _set_kyc_error(self, message):
        """Store error message on this input record (shown on the thank-you page)."""
        _logger.error("KYC survey (input %s): %s", self.id, message)
        try:
            self.sudo().write({'kyc_error_message': message})
        except Exception:
            pass  # Don't let error storage itself break anything

    def _save_kyc_record(self, values, attachments_by_field, vendor_email, overseas=False):
        """Find partner, create/update KYC record, update partner flags."""
        # Finalise many2many attachment commands
        KycModel = self.env['res.partner.kyc.approval']
        for field_name, att_ids in attachments_by_field.items():
            field = KycModel._fields.get(field_name)
            if field and field.type == 'many2many':
                values[field_name] = [(6, 0, att_ids)]

        _logger.info("KYC survey (input %s): email=%r keys=%s", self.id, vendor_email, list(values.keys()))

        if not vendor_email:
            self._set_kyc_error(
                "Your KYC form was submitted but we could not link it to your account because "
                "no email address was found in your submission. Please contact your point of contact "
                "at Bora Multicorp to resolve this."
            )
            return

        partner = self._find_partner_by_email(vendor_email, overseas=overseas)
        if not partner:
            self._set_kyc_error(
                f"Your KYC form was submitted but no registered contact was found for the email address "
                f"'{vendor_email}'. Please ensure your email matches the one registered in our system, "
                f"or contact your point of contact at Bora Multicorp."
            )
            return

        _logger.info("KYC survey (input %s): matched partner '%s' (id=%s)", self.id, partner.name, partner.id)
        values['partner_id'] = partner.id

        try:
            existing_kyc = KycModel.search(
                [('partner_id', '=', partner.id)], order='create_date desc', limit=1
            )

            # For overseas partners, always update existing record (handles expired + rejected cases
            # where is_kyc may still be True because the partner already has an approved record).
            if existing_kyc and (not partner.is_kyc or overseas):
                # Re-KYC: clear o2m children first, then update
                _logger.info("KYC survey (input %s): Re-KYC — updating record %s", self.id, existing_kyc.id)
                for director in existing_kyc.directors_detail:
                    director.write({
                        'aadhaar_card_attachments': [(5,)],
                        'pan_card_attachments': [(5,)],
                        'govt_id_attachments': [(5,)],
                    })
                for bank in existing_kyc.bank_detail:
                    bank.write({'bank_cheque_attachments': [(5,)]})
                for k in ('directors_detail', 'bank_detail', 'address_detail'):
                    if isinstance(values.get(k), list):
                        values[k] = [(5,)] + values[k]
                existing_kyc.write(values)
                kyc_record = existing_kyc
            else:
                _logger.info("KYC survey (input %s): creating new KYC record for partner %s", self.id, partner.id)
                kyc_record = KycModel.create(values)

            # Rebind attachments to the KYC record so they appear in its chatter/files
            all_att_ids = [aid for ids in attachments_by_field.values() for aid in ids]
            if all_att_ids:
                self.env['ir.attachment'].sudo().browse(all_att_ids).write({
                    'res_model': 'res.partner.kyc.approval',
                    'res_id': kyc_record.id,
                })

            partner.write({
                'is_kyc': True,
                'rejection_date': False,
                'rejection_reason': False,
                'is_rejected': False,
            })
            _logger.info("KYC record %s saved OK for partner %s", kyc_record.id, partner.id)

        except Exception as e:
            _logger.exception("KYC survey (input %s): unexpected error saving KYC record", self.id)
            self._set_kyc_error(
                f"Your KYC form was received but could not be saved due to a technical error: {e}. "
                f"Please contact your point of contact at Bora Multicorp with this message."
            )

    # -------------------------------------------------------------------------
    # _mark_done override
    # -------------------------------------------------------------------------

    def _mark_done(self):
        super()._mark_done()

        vendor_survey = self.env.ref("ks_contact.vendor_kyc_form_survey", raise_if_not_found=False)
        overseas_survey = self.env.ref("ks_contact.overseas_kyc_form_survey", raise_if_not_found=False)

        if overseas_survey and self.survey_id == overseas_survey:
            self._process_overseas_kyc_survey()
        elif vendor_survey and self.survey_id == vendor_survey:
            self._process_vendor_kyc_survey()

    # -------------------------------------------------------------------------
    # Indian vendor KYC survey
    # -------------------------------------------------------------------------

    def _process_vendor_kyc_survey(self):
        Q = self.env.ref
        KycModel = self.env['res.partner.kyc.approval']

        # email question handled separately (not a field on KYC model)
        email_q = Q("ks_contact.email_kyc_survey", raise_if_not_found=False)

        question_map = {
            Q("ks_contact.point_of_contact_kyc_survey").id:            "point_of_contact",
            Q("ks_contact.company_point_of_contact_kyc_survey").id:    "poc_user",
            Q("ks_contact.business_name_kyc_survey").id:               "business_legal_name",
            Q("ks_contact.is_same_trade_name_kyc_survey").id:          "is_same_trade_name",
            Q("ks_contact.business_trade_name_kyc_survey").id:         "business_trade_name",
            Q("ks_contact.business_constitution_kyc_survey").id:       "const_business",
            Q("ks_contact.no_of_director_kyc_survey").id:              "no_partner_director",
            Q("ks_contact.gst_no_kyc_survey").id:                      "gst_no",
            Q("ks_contact.pan_card_no_kyc_survey").id:                 "pan_no",
            Q("ks_contact.pan_card_document_kyc_survey").id:           "pan_card_document",
            Q("ks_contact.aadhaar_pan_link_kyc_survey").id:            "aadhaar_pan_link",
            Q("ks_contact.registration_kyc_survey").id:                "license_registered",
            Q("ks_contact.udyam_certificate_kyc_survey").id:           "udyam_number",
            Q("ks_contact.gst_duration_kyc_survey").id:                "gst_return_duration",
            Q("ks_contact.gst_certificate_kyc_survey").id:             "gst_certificate",
            Q("ks_contact.shop_act_document_kyc_survey").id:           "shop_act_document",
            Q("ks_contact.udyam_document_kyc_survey").id:              "udyam_document",
            Q("ks_contact.shop_photos_kyc_survey").id:                 "shop_photos",
            Q("ks_contact.shop_videos_kyc_survey").id:                 "shop_videos",
            Q("ks_contact.comp_google_loc_kyc_survey").id:             "comp_google_loc",
            Q("ks_contact.partnership_llp_kyc_survey").id:             "partner_llp",
            Q("ks_contact.incorporation_certificate_kyc_survey").id:   "incorporation_certificate",
            Q("ks_contact.moa_aoa_kyc_survey").id:                     "moa_aoa",
            Q("ks_contact.cin_no_kyc_survey").id:                      "cin_no",
            Q("ks_contact.electricity_bill_kyc_survey").id:            "electricity_bill",
        }
        matrix_q_ids = {
            Q("ks_contact.matrix_bank_address_kyc_survey").id:      "bank",
            Q("ks_contact.matrix_director_detail_kyc_survey").id:   "director",
            Q("ks_contact.matrix_address_detail_kyc_survey").id:    "address",
        }

        values = {}
        attachments_by_field = {}
        vendor_email = (self.email or '').strip()
        processed_matrix_ids = set()

        for line in self.user_input_line_ids:
            q_id = line.question_id.id
            qtype = line.question_id.question_type

            # Extract email for partner lookup
            if email_q and q_id == email_q.id:
                if not vendor_email:
                    vendor_email = (line.value_char_box or '').strip()
                continue

            field_name = question_map.get(q_id)
            if field_name:
                field = KycModel._fields.get(field_name)
                if qtype in ("char_box", "text_box"):
                    values[field_name] = line.value_char_box
                elif qtype == "simple_choice":
                    values[field_name] = line.suggested_answer_id.value or line.value_char_box
                elif qtype == "multiple_choice":
                    values[field_name] = ",".join(line.suggested_answer_ids.mapped("value")) or line.value_char_box
                elif qtype == "que_sh_many2one":
                    user = self.env['res.users'].search([('name', '=', line.suggested_answer_id.value)], limit=1)
                    values[field_name] = user.id if user else False
                elif qtype == "que_sh_file" and field:
                    self._parse_file_line(line, field, field_name, attachments_by_field, values)
                continue

            matrix_type = matrix_q_ids.get(q_id)
            if matrix_type and q_id not in processed_matrix_ids:
                processed_matrix_ids.add(q_id)
                row_data_map, line_map = self._build_matrix_maps(line.question_id)

                if matrix_type == "bank":
                    values['bank_detail'] = []
                    for row_id, row in row_data_map.items():
                        cheque_file = row.get('Cancelled Cheque')
                        cheque_ml = line_map[row_id].get('Cancelled Cheque')
                        cheque_fname = (cheque_ml.value_ans_sh_file_fname if cheque_ml else None) or 'cheque'
                        values['bank_detail'].append((0, 0, {
                            'bank_name': row.get('Bank Name'),
                            'account_no': row.get('Account Number'),
                            'ifsc_code': row.get('IFSC Code'),
                            'bank_cheque_attachments': [(0, 0, {'name': cheque_fname, 'type': 'binary', 'datas': cheque_file})] if cheque_file else False,
                        }))

                elif matrix_type == "director":
                    values['directors_detail'] = []
                    for row_id, row in row_data_map.items():
                        def _att(col, _row=row, _lmap=line_map, _row_id=row_id):
                            f = _row.get(col)
                            ml = _lmap[_row_id].get(col)
                            fname = (ml.value_ans_sh_file_fname if ml else None) or col
                            return [(0, 0, {'name': fname, 'datas': f, 'type': 'binary'})] if f else False
                        values['directors_detail'].append((0, 0, {
                            'designation': row.get('Designation'),
                            'name': row.get('Name'),
                            'contact_no': row.get('Contact Number'),
                            'email': row.get('Email Address'),
                            'aadhaar_card_attachments': _att('Aadhaar Card'),
                            'pan_card_attachments': _att('PAN Card'),
                        }))

                elif matrix_type == "address":
                    values['address_detail'] = [
                        (0, 0, {
                            'business_street': row.get('Address'),
                            'business_city': row.get('City Name'),
                            'business_pincode': row.get('Pincode'),
                            'business_phone': row.get('Contact Number'),
                            'business_email': row.get('Email'),
                            'business_state_id': self.env['res.country.state'].search(
                                [('name', '=', row.get('State'))], limit=1).id or False,
                            'business_country_id': self.env['res.country'].search(
                                [('name', '=', row.get('Country'))], limit=1).id or False,
                        })
                        for row in row_data_map.values()
                    ]

        self._save_kyc_record(values, attachments_by_field, vendor_email)

    # -------------------------------------------------------------------------
    # Overseas KYC survey
    # -------------------------------------------------------------------------

    def _process_overseas_kyc_survey(self):
        Q = self.env.ref
        KycModel = self.env['res.partner.kyc.approval']

        email_q = Q("ks_contact.overseas_email_kyc_survey", raise_if_not_found=False)

        question_map = {
            Q("ks_contact.overseas_poc_kyc_survey").id:              "point_of_contact",
            Q("ks_contact.overseas_company_poc_kyc_survey").id:      "poc_user",
            Q("ks_contact.overseas_business_name_kyc_survey").id:    "business_legal_name",
            Q("ks_contact.overseas_same_trade_name_kyc_survey").id:  "is_same_trade_name",
            Q("ks_contact.overseas_trade_name_kyc_survey").id:       "business_trade_name",
            Q("ks_contact.overseas_const_business_kyc_survey").id:   "const_business",
            Q("ks_contact.overseas_no_directors_kyc_survey").id:     "no_partner_director",
            Q("ks_contact.overseas_company_reg_doc_kyc_survey").id:  "company_reg_document",
            Q("ks_contact.overseas_company_reg_doc_expiry_survey").id: "company_reg_doc_expiry",
            Q("ks_contact.overseas_auth_person_id_doc_kyc_survey").id: "authorized_person_id_document",
            Q("ks_contact.overseas_auth_person_id_expiry_survey").id:  "authorized_person_id_expiry",
        }
        matrix_q_ids = {
            Q("ks_contact.overseas_matrix_bank_kyc_survey").id:      "bank",
            Q("ks_contact.overseas_matrix_director_kyc_survey").id:  "director",
            Q("ks_contact.overseas_matrix_address_kyc_survey").id:   "address",
        }

        values = {}
        attachments_by_field = {}
        vendor_email = (self.email or '').strip()
        processed_matrix_ids = set()

        for line in self.user_input_line_ids:
            q_id = line.question_id.id
            qtype = line.question_id.question_type

            # Extract email for partner lookup
            if email_q and q_id == email_q.id:
                if not vendor_email:
                    vendor_email = (line.value_char_box or '').strip()
                continue

            field_name = question_map.get(q_id)
            if field_name:
                field = KycModel._fields.get(field_name)
                if qtype in ("char_box", "text_box"):
                    values[field_name] = line.value_char_box
                elif qtype == "date":
                    values[field_name] = line.value_date or False
                elif qtype == "simple_choice":
                    values[field_name] = line.suggested_answer_id.value or line.value_char_box
                elif qtype == "que_sh_many2one":
                    user = self.env['res.users'].search([('name', '=', line.suggested_answer_id.value)], limit=1)
                    values[field_name] = user.id if user else False
                elif qtype == "que_sh_file" and field:
                    self._parse_file_line(line, field, field_name, attachments_by_field, values)
                continue

            matrix_type = matrix_q_ids.get(q_id)
            if matrix_type and q_id not in processed_matrix_ids:
                processed_matrix_ids.add(q_id)
                row_data_map, line_map = self._build_matrix_maps(line.question_id)

                if matrix_type == "bank":
                    values['bank_detail'] = []
                    for row_id, row in row_data_map.items():
                        cheque_file = row.get('Cancelled Cheque')
                        cheque_ml = line_map[row_id].get('Cancelled Cheque')
                        cheque_fname = (cheque_ml.value_ans_sh_file_fname if cheque_ml else None) or 'cheque'
                        values['bank_detail'].append((0, 0, {
                            'bank_name': row.get('Bank Name'),
                            'account_no': row.get('Account Number'),
                            'ifsc_code': row.get('SWIFT Code'),
                            'iban_no': row.get('IBAN No') or False,
                            'intermediate_bank_code': row.get('Intermediate Bank Code') or False,
                            'bank_cheque_attachments': [(0, 0, {'name': cheque_fname, 'type': 'binary', 'datas': cheque_file})] if cheque_file else False,
                        }))

                elif matrix_type == "director":
                    values['directors_detail'] = []
                    for row_id, row in row_data_map.items():
                        govt_id_file = row.get('Govt. ID (Passport / Emirates ID / HKID)')
                        govt_id_ml = line_map[row_id].get('Govt. ID (Passport / Emirates ID / HKID)')
                        govt_id_fname = (govt_id_ml.value_ans_sh_file_fname if govt_id_ml else None) or 'govt_id'
                        govt_id_expiry = row.get('Govt. ID Expiry Date') or False
                        values['directors_detail'].append((0, 0, {
                            'designation': row.get('Designation'),
                            'name': row.get('Name'),
                            'contact_no': row.get('Contact Number'),
                            'email': row.get('Email Address'),
                            'govt_id_attachments': [(0, 0, {'name': govt_id_fname, 'type': 'binary', 'datas': govt_id_file})] if govt_id_file else False,
                            'govt_id_expiry': govt_id_expiry,
                        }))

                elif matrix_type == "address":
                    values['address_detail'] = [
                        (0, 0, {
                            'business_street': row.get('Address'),
                            'business_city': row.get('City Name'),
                            'business_pincode': row.get('Postcode'),
                            'business_phone': row.get('Contact Number'),
                            'business_email': row.get('Email'),
                            'business_state_id': self.env['res.country.state'].search(
                                [('name', '=', row.get('State / Emirate / Region'))], limit=1).id or False,
                            'business_country_id': self.env['res.country'].search(
                                [('name', '=', row.get('Country'))], limit=1).id or False,
                        })
                        for row in row_data_map.values()
                    ]

        self._save_kyc_record(values, attachments_by_field, vendor_email, overseas=True)
