# -*- coding: utf-8 -*-
import logging
from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def action_testing(self):
        """Placeholder test method"""
        pass

    # -------------------------------------------------------------------------
    # Helper: Find vendor partner by email
    # -------------------------------------------------------------------------
    def _find_partner_by_email(self, email):
        """Return vendor partner matching the given email."""
        if not email:
            return self.env['res.partner'].browse([])
        return self.env['res.partner'].sudo().search([
            ('email', '=ilike', email),
            ('is_vendor', '=', True)
        ], limit=1)

    # -------------------------------------------------------------------------
    # Main: Executed when survey is marked as done
    # -------------------------------------------------------------------------
    def _mark_done(self):
        """Override to create a KYC approval record from survey results."""
        super()._mark_done()

        # Fetch Vendor KYC Survey Reference
        vendor_survey = self.env.ref("ks_contact.vendor_kyc_form_survey", raise_if_not_found=False)
        if not vendor_survey or self.survey_id != vendor_survey:
            return

        Q = self.env.ref

        # Mapping Survey Questions → KYC Model Fields
        question_map = {
            Q("ks_contact.email_kyc_survey").id: "email",
            Q("ks_contact.point_of_contact_kyc_survey").id: "point_of_contact",
            Q("ks_contact.company_point_of_contact_kyc_survey").id: "poc_user",
            Q("ks_contact.business_name_kyc_survey").id: "business_legal_name",
            Q("ks_contact.is_same_trade_name_kyc_survey").id: "is_same_trade_name",
            Q("ks_contact.business_trade_name_kyc_survey").id: "business_trade_name",
            Q("ks_contact.business_constitution_kyc_survey").id: "const_business",
            Q("ks_contact.no_of_director_kyc_survey").id: "no_partner_director",
            Q("ks_contact.gst_no_kyc_survey").id: "gst_no",
            Q("ks_contact.pan_card_no_kyc_survey").id: "pan_no",
            Q("ks_contact.pan_card_document_kyc_survey").id: "pan_card_document",
            Q("ks_contact.aadhaar_pan_link_kyc_survey").id: "aadhaar_pan_link",
            Q("ks_contact.registration_kyc_survey").id: "license_registered",
            Q("ks_contact.udyam_certificate_kyc_survey").id: "udyam_number",
            Q("ks_contact.gst_duration_kyc_survey").id: "gst_return_duration",
            Q("ks_contact.gst_certificate_kyc_survey").id: "gst_certificate",
            Q("ks_contact.shop_act_document_kyc_survey").id: "shop_act_document",
            Q("ks_contact.udyam_document_kyc_survey").id: "udyam_document",
            Q("ks_contact.shop_photos_kyc_survey").id: "shop_photos",
            Q("ks_contact.shop_videos_kyc_survey").id: "shop_videos",
            Q("ks_contact.comp_google_loc_kyc_survey").id: "comp_google_loc",
            Q("ks_contact.partnership_llp_kyc_survey").id: "partner_llp",
            Q("ks_contact.incorporation_certificate_kyc_survey").id: "incorporation_certificate",
            Q("ks_contact.moa_aoa_kyc_survey").id: "moa_aoa",
            Q("ks_contact.cin_no_kyc_survey").id: "cin_no",
            Q("ks_contact.electricity_bill_kyc_survey").id: "electricity_bill",
            Q("ks_contact.matrix_bank_address_kyc_survey").id: "bank_detail",
            Q("ks_contact.matrix_director_detail_kyc_survey").id: "directors_detail",
            Q("ks_contact.matrix_address_detail_kyc_survey").id: "address_detail",
        }

        values = {}                     # Stores parsed answers → KYC create data
        attachments_by_field = {}       # Collect attachment IDs for many2many

        # -------------------------------------------------------------------------
        # Extract responses from each answered line
        # -------------------------------------------------------------------------
        for line in self.user_input_line_ids:

            field_name = question_map.get(line.question_id.id)
            if not field_name:
                continue

            qtype = line.question_id.question_type
            field = self.env['res.partner.kyc.approval']._fields.get(field_name)

            # ---------------- TEXT INPUT ----------------
            if qtype in ("char_box", "text_box"):
                values[field_name] = line.value_char_box

            # ---------------- SINGLE CHOICE ----------------
            elif qtype == "simple_choice":
                values[field_name] = line.suggested_answer_id.value or line.value_char_box

            # ---------------- MULTIPLE CHOICE ----------------
            elif qtype == "multiple_choice":
                values[field_name] = ",".join(line.suggested_answer_ids.mapped("value")) or line.value_char_box

            # ---------------- USER MANY2ONE ----------------
            elif qtype == "que_sh_many2one":
                user = self.env['res.users'].search([('name', '=', line.suggested_answer_id.value)], limit=1)
                values[field_name] = user.id if user else False

            # ---------------- FILE FIELD ----------------
            elif qtype == "que_sh_file" and field:
                file_data = line.value_ans_sh_file
                file_name = line.value_ans_sh_file_fname or f"unnamed_file_{line.id}"
                if not file_data:
                    continue

                def _create_attachment(fname, data):
                    """Create attachment and return ID."""
                    att = self.env['ir.attachment'].create({
                        'name': fname,
                        'datas': data,
                        'type': 'binary',
                    })
                    return att.id

                # Handle multiple files
                if isinstance(file_data, list):
                    att_ids = []
                    for entry in file_data:
                        datas = entry.get("value")
                        fname = entry.get("filename") or file_name
                        if not datas:
                            continue

                        if field.type == 'binary':
                            values[field_name] = datas
                        elif field.type == 'many2many':
                            att_ids.append(_create_attachment(fname, datas))

                    if att_ids:
                        attachments_by_field.setdefault(field_name, []).extend(att_ids)

                # Handle single file
                else:
                    if field.type == 'binary':
                        values[field_name] = file_data
                    else:
                        att_id = _create_attachment(file_name, file_data)
                        attachments_by_field.setdefault(field_name, []).append(att_id)

            # ---------------- MATRIX QUESTIONS ----------------
            elif qtype == "matrix":
                matrix_lines = self.user_input_line_ids.filtered(
                    lambda l: l.question_id.id == line.question_id.id
                    and l.matrix_row_id and l.answer_type
                )

                row_data_map = {}
                line_map = {}

                # Build row → col → value map
                for ml in matrix_lines:
                    row_id = ml.matrix_row_id.id
                    col_name = ml.suggested_answer_id.value or ml.answer_id.value
                    if not col_name:
                        continue

                    value = getattr(ml, f"value_{ml.answer_type}")
                    if isinstance(value, models.BaseModel):
                        value = value.id

                    row_data_map.setdefault(row_id, {})[col_name] = value
                    line_map.setdefault(row_id, {})[col_name] = ml

                # --- Matrix: Bank Details ---
                if line.question_id.id == Q("ks_contact.matrix_bank_address_kyc_survey").id:
                    values['bank_detail'] = []

                    for row_id, row in row_data_map.items():
                        cheque_file = row.get('Cancelled Cheque')
                        cheque_line = line_map[row_id].get('Cancelled Cheque')

                        cheque_name = cheque_line.value_ans_sh_file_fname if cheque_line else 'Cancelled Cheque'
                        cheque_att = [(0, 0, {'name': cheque_name, 'type': 'binary', 'datas': cheque_file})] if cheque_file else False

                        values['bank_detail'].append((0, 0, {
                            'bank_name': row.get('Bank Name'),
                            'account_no': row.get('Account Number'),
                            'ifsc_code': row.get('IFSC Code'),
                            'bank_address': row.get('Bank Address'),
                            'bank_cheque_attachments': cheque_att,
                        }))

                # --- Matrix: Director Details ---
                elif line.question_id.id == Q("ks_contact.matrix_director_detail_kyc_survey").id:
                    values['directors_detail'] = []

                    for row_id, row in row_data_map.items():

                        def _prepare_file(col):
                            f = row.get(col)
                            l = line_map[row_id].get(col)
                            fname = l.value_ans_sh_file_fname if l else col
                            return [(0, 0, {'name': fname, 'datas': f, 'type': 'binary'})] if f else False

                        aadhaar_att = _prepare_file('Aadhaar Card')
                        pan_att = _prepare_file('PAN Card')

                        values['directors_detail'].append((0, 0, {
                            'designation': row.get('Designation'),
                            'name': row.get('Name'),
                            'contact_no': row.get('Contact Number'),
                            'email': row.get('Email Address'),
                            'aadhaar_card_attachments': aadhaar_att,
                            'pan_card_attachments': pan_att,
                        }))

                # --- Matrix: Address Details ---
                elif line.question_id.id == Q("ks_contact.matrix_address_detail_kyc_survey").id:
                    values['address_detail'] = [
                        (0, 0, {
                            'business_street': row.get('Address'),
                            'business_city': row.get('City Name'),
                            'business_pincode': row.get('Pincode'),
                            'business_phone': row.get('Contact Number'),
                            'business_email': row.get('Email'),
                            'business_state_id': self.env['res.country.state'].search([('name', '=', row.get('State'))], limit=1).id,
                            'business_country_id': self.env['res.country'].search([('name', '=', row.get('Country'))], limit=1).id,
                        })
                        for row in row_data_map.values()
                    ]

        # -------------------------------------------------------------------------
        # Attach many2many file attachments (M2M → Attachments)
        # -------------------------------------------------------------------------
        for field_name, att_ids in attachments_by_field.items():
            field = self.env['res.partner.kyc.approval']._fields.get(field_name)

            if not field:
                continue

            if field.type == 'many2many':
                values[field_name] = [(6, 0, att_ids)]
            elif field.type != 'binary':
                raise UserError(_("Unsupported file field type for field: %s") % field_name)

        # -------------------------------------------------------------------------
        # Create or Update KYC Record If Data Exists
        # -------------------------------------------------------------------------
        if values:
            vendor_email = (self.email or '').strip()
            partner = self._find_partner_by_email(vendor_email)

            if partner:
                values['partner_id'] = partner.id

                try:
                    # Check if this is Re-KYC (existing KYC record exists)
                    existing_kyc = self.env['res.partner.kyc.approval'].search([
                        ('partner_id', '=', partner.id)
                    ], order='create_date desc', limit=1)
                    
                    if existing_kyc and not partner.is_kyc:
                        # Re-KYC: Update existing record
                        kyc_record = existing_kyc
                        
                        # Clear existing One2many records by first clearing Many2many attachments
                        # This prevents foreign key constraint errors
                        for director in kyc_record.directors_detail:
                            # Clear Many2many relationships first
                            director.write({
                                'aadhaar_card_attachments': [(5, 0, 0)],
                                'pan_card_attachments': [(5, 0, 0)],
                            })
                        
                        for bank in kyc_record.bank_detail:
                            # Clear Many2many relationships first
                            bank.write({
                                'bank_cheque_attachments': [(5, 0, 0)],
                            })
                        
                        # Use ORM commands to clear and replace One2many records
                        if 'directors_detail' in values:
                            # Prepend (5, 0, 0) to clear all existing records
                            if isinstance(values['directors_detail'], list):
                                values['directors_detail'] = [(5, 0, 0)] + values['directors_detail']
                        if 'bank_detail' in values:
                            if isinstance(values['bank_detail'], list):
                                values['bank_detail'] = [(5, 0, 0)] + values['bank_detail']
                        if 'address_detail' in values:
                            if isinstance(values['address_detail'], list):
                                values['address_detail'] = [(5, 0, 0)] + values['address_detail']
                        
                        # Update the record
                        kyc_record.write(values)
                        
                        # Rebind attachments to updated KYC record
                        for field_name in attachments_by_field:
                            att_m2m_value = values.get(field_name)
                            if att_m2m_value and att_m2m_value[0][0] == 6:
                                att_ids = att_m2m_value[0][2]
                                self.env['ir.attachment'].browse(att_ids).sudo().write({
                                    'res_model': 'res.partner.kyc.approval',
                                    'res_id': kyc_record.id,
                                })
                        
                        # Log Re-KYC update in chatter
                        kyc_record.message_post(
                            body=_("Re-KYC Form Updated via Survey by %s") % (self.env.user.name if self.env.user else 'System'),
                            message_type="comment",
                            subtype_xmlid="mail.mt_note",
                        )
                    else:
                        # New KYC: Create new record
                        kyc_record = self.env['res.partner.kyc.approval'].create(values)

                        # Rebind attachments to newly created KYC record
                        for field_name in attachments_by_field:
                            att_m2m_value = values.get(field_name)
                            if att_m2m_value and att_m2m_value[0][0] == 6:
                                att_ids = att_m2m_value[0][2]
                                self.env['ir.attachment'].browse(att_ids).sudo().write({
                                    'res_model': 'res.partner.kyc.approval',
                                    'res_id': kyc_record.id,
                                })

                    # Update partner KYC status
                    partner.write({
                        'is_kyc': True,
                        'rejection_date': False,
                        'rejection_reason': False,
                        'is_rejected': False,
                    })

                except Exception as e:
                    _logger.exception("Error while creating/updating KYC for email: %s", vendor_email)
                    self.env['ir.logging'].sudo().create({
                        'type': 'server',
                        'name': 'KYC Creation/Update Error',
                        'level': 'DEBUG',
                        'path': 'res.partner.kyc.approval',
                        'func': '_mark_done',
                        'line': 1,
                        'message': f"Error creating/updating KYC for email: {vendor_email}. Exception: {e}"
                    })
                    return False
