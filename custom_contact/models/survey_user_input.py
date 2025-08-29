# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def action_testing(self):
        pass

    def _mark_done(self):
        super()._mark_done()  # Ensure the base behavior is triggered
        vendor_survey = self.env.ref("custom_contact.vendor_kyc_form_survey", raise_if_not_found=False)
        if not vendor_survey or self.survey_id != vendor_survey:
            return

        Q = self.env.ref
        question_map = {
            Q("custom_contact.email_kyc_survey").id: "email",
            Q("custom_contact.point_of_contact_kyc_survey").id: "point_of_contact",
            Q("custom_contact.company_point_of_contact_kyc_survey").id: "poc_user",
            Q("custom_contact.business_name_kyc_survey").id: "business_legal_name",
            Q("custom_contact.is_same_trade_name_kyc_survey").id: "is_same_trade_name",
            Q("custom_contact.business_trade_name_kyc_survey").id: "business_trade_name",
            Q("custom_contact.business_constitution_kyc_survey").id: "const_business",
            Q("custom_contact.no_of_director_kyc_survey").id: "no_partner_director",
            Q("custom_contact.gst_no_kyc_survey").id: "gst_no",
            Q("custom_contact.pan_card_no_kyc_survey").id: "pan_no",
            Q("custom_contact.pan_card_document_kyc_survey").id: "pan_card_document",
            Q("custom_contact.aadhaar_pan_link_kyc_survey").id: "aadhaar_pan_link",
            Q("custom_contact.registration_kyc_survey").id: "license_registered",
            Q("custom_contact.udyam_certificate_kyc_survey").id: "udyam_number",
            Q("custom_contact.gst_duration_kyc_survey").id: "gst_return_duration",
            Q("custom_contact.gst_certificate_kyc_survey").id: "gst_certificate",
            Q("custom_contact.shop_act_document_kyc_survey").id: "shop_act_document",
            Q("custom_contact.udyam_document_kyc_survey").id: "udyam_document",
            Q("custom_contact.shop_photos_kyc_survey").id: "shop_photos",
            Q("custom_contact.shop_videos_kyc_survey").id: "shop_videos",
            Q("custom_contact.comp_google_loc_kyc_survey").id: "comp_google_loc",
            Q("custom_contact.partnership_llp_kyc_survey").id: "partner_llp",
            Q("custom_contact.incorporation_certificate_kyc_survey").id: "incorporation_certificate",
            Q("custom_contact.moa_aoa_kyc_survey").id: "moa_aoa",
            Q("custom_contact.cin_no_kyc_survey").id: "cin_no",
            Q("custom_contact.electricity_bill_kyc_survey").id: "electricity_bill",
            Q("custom_contact.matrix_bank_address_kyc_survey").id: "bank_detail",
            Q("custom_contact.matrix_director_detail_kyc_survey").id: "directors_detail",
            Q("custom_contact.matrix_address_detail_kyc_survey").id: "address_detail",
        }

        values = {}
        attachments_by_field = {}

        for line in self.user_input_line_ids:
            field_name = question_map.get(line.question_id.id)
            if not field_name:
                continue

            qtype = line.question_id.question_type
            field = self.env['res.partner.kyc.approval']._fields.get(field_name)

            if qtype in ("char_box", "text_box"):
                values[field_name] = line.value_char_box

            elif qtype == "simple_choice":
                values[field_name] = line.suggested_answer_id.value or line.value_char_box

            elif qtype == "multiple_choice":
                values[field_name] = ",".join(line.suggested_answer_ids.mapped("value")) or line.value_char_box

            elif qtype == "que_sh_many2one":
                record = self.env['res.users'].search([
                    ('name', '=', line.suggested_answer_id.value)
                ], limit=1)
                values[field_name] = record.id if record else False

            elif qtype == "que_sh_file" and field:
                file_data = line.value_ans_sh_file
                file_name = line.value_ans_sh_file_fname or f"unnamed_file_{line.id}"
                if not file_data:
                    continue

                if isinstance(file_data, list):
                    attachments = []
                    for entry in file_data:
                        datas = entry.get("value")
                        fname = entry.get("filename") or file_name
                        if not datas:
                            continue
                        if field.type == 'binary':
                            values[field_name] = datas
                        elif field.type == 'many2many':
                            attachment = self.env['ir.attachment'].create({
                                'name': fname,
                                'datas': datas,
                                'type': 'binary',
                            })
                            attachments.append(attachment.id)
                    if attachments:
                        attachments_by_field.setdefault(field_name, []).extend(attachments)

                elif isinstance(file_data, (bytes, str)):
                    if field.type == 'binary':
                        values[field_name] = file_data
                    elif field.type == 'many2many':
                        attachment = self.env['ir.attachment'].create({
                            'name': file_name,
                            'datas': file_data,
                            'type': 'binary',
                        })
                        attachments_by_field.setdefault(field_name, []).append(attachment.id)

            elif qtype == "matrix":
                matrix_lines = self.user_input_line_ids.filtered(
                    lambda l: l.question_id.id == line.question_id.id and l.matrix_row_id and l.answer_type
                )
                row_data_map = {}
                line_map = {}
                for ml in matrix_lines:
                    row_key = ml.matrix_row_id.id
                    col_key = ml.suggested_answer_id.value or ml.answer_id.value
                    if not col_key:
                        continue
                    value = getattr(ml, f"value_{ml.answer_type}", None)
                    if isinstance(value, models.BaseModel):
                        value = value.id
                    row_data_map.setdefault(row_key, {})[col_key] = value
                    line_map.setdefault(row_key, {})[col_key] = ml

                if line.question_id.id == Q("custom_contact.matrix_bank_address_kyc_survey").id:
                    values['bank_detail'] = []
                    for row_id, row in row_data_map.items():
                        cheque_file = row.get('Cancelled Cheque')
                        cheque_name = 'Cancelled Cheque'
                        cheque_line = line_map[row_id].get('Cancelled Cheque')
                        if cheque_line and cheque_line.value_ans_sh_file_fname:
                            cheque_name = cheque_line.value_ans_sh_file_fname
                        attachment_id = (
                            self.env['ir.attachment'].create({
                                'name': cheque_name,
                                'type': 'binary',
                                'datas': cheque_file,
                            }).id if cheque_file else False
                        )
                        values['bank_detail'].append((0, 0, {
                            'bank_name': row.get('Bank Name'),
                            'account_no': row.get('Account Number'),
                            'ifsc_code': row.get('IFSC Code'),
                            'bank_address': row.get('Bank Address'),
                            'bank_cheque_attachments': [(6, 0, [attachment_id])] if attachment_id else False,
                        }))

                elif line.question_id.id == Q("custom_contact.matrix_director_detail_kyc_survey").id:
                    values['directors_detail'] = []
                    for row_id, row in row_data_map.items():
                        aadhaar_file = row.get('Aadhaar Card')
                        aadhaar_name = 'Aadhaar Card'
                        aadhaar_line = line_map[row_id].get('Aadhaar Card')
                        if aadhaar_line and aadhaar_line.value_ans_sh_file_fname:
                            aadhaar_name = aadhaar_line.value_ans_sh_file_fname
                        aadhaar_attachment_id = (
                            self.env['ir.attachment'].create({
                                'name': aadhaar_name,
                                'type': 'binary',
                                'datas': aadhaar_file,
                            }).id if aadhaar_file else False
                        )

                        # PAN file
                        pan_file = row.get('PAN Card')
                        pan_name = 'PAN Card'
                        pan_line = line_map[row_id].get('PAN Card')
                        if pan_line and pan_line.value_ans_sh_file_fname:
                            pan_name = pan_line.value_ans_sh_file_fname
                        pan_attachment_id = (
                            self.env['ir.attachment'].create({
                                'name': pan_name,
                                'type': 'binary',
                                'datas': pan_file,
                            }).id if pan_file else False
                        )
                        # aadhaar_line = line_map[row_id].get('Aadhaar Card')
                        # pan_line = line_map[row_id].get('PAN Card')
                        values['directors_detail'].append((0, 0, {
                            'designation': row.get('Designation'),
                            'name': row.get('Name'),
                            'contact_no': row.get('Contact Number'),
                            'email': row.get('Email Address'),
                            'aadhaar_card_attachments': [(6, 0, [aadhaar_attachment_id])] if aadhaar_attachment_id else False,
                            'pan_card_attachments': [(6, 0, [pan_attachment_id])] if pan_attachment_id else False,
                            # 'aadhaar_card': row.get('Aadhaar Card'),
                            # 'aadhaar_card_filename': aadhaar_line.value_ans_sh_file_fname if aadhaar_line else False,
                            # 'pan_card': row.get('PAN Card'),
                            # 'pan_card_filename': pan_line.value_ans_sh_file_fname if pan_line else False,
                        }))

                elif line.question_id.id == Q("custom_contact.matrix_address_detail_kyc_survey").id:
                    values['address_detail'] = [(0, 0, {
                        'business_street': row.get('Address'),
                        'business_city': row.get('City Name'),
                        'business_pincode': row.get('Pincode'),
                        'business_phone': row.get('Contact Number'),
                        'business_email': row.get('Email'),
                        'business_state_id': self.env['res.country.state'].search([('name', '=', row.get('State'))],
                                                                                  limit=1).id or False,
                        'business_country_id': self.env['res.country'].search([('name', '=', row.get('Country'))],
                                                                              limit=1).id or False,
                    }) for row in row_data_map.values()]

        for field_name, attachment_ids in attachments_by_field.items():
            field = self.env['res.partner.kyc.approval']._fields.get(field_name)
            if not field:
                continue
            if field.type == 'many2many':
                values[field_name] = [(6, 0, attachment_ids)]
            elif field.type != 'binary':
                raise UserError(_("Unsupported field type '%s' for file field '%s'.") % (field.type, field_name))

        if values:
            partner = self.partner_id or self.env['res.partner'].search([('email', '=ilike', self.email)], limit=1)
            if partner:
                values['partner_id'] = partner.id
                kyc_record = self.env['res.partner.kyc.approval'].create(values)
                if kyc_record:
                    # for bank in kyc_record.bank_detail:
                    #     for att in bank.bank_cheque_attachments:
                    #         att.write({'res_id': bank.id})
                    partner.write({
                        'is_kyc': True,
                        'rejection_date': False,
                        'rejection_reason': False,
                        'is_rejected': False,
                    })
