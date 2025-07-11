# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError
import base64

class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def action_testing(self):
        pass

    def _mark_done(self):
        super()._mark_done()  # Ensure the base behavior is triggered
        vendor_survey = self.env.ref(
            "custom_contact.vendor_kyc_form_survey", raise_if_not_found=False
        )
        if not vendor_survey or self.survey_id != vendor_survey:
            return  # We only process the vendor KYC form

        Q = self.env.ref  # shortcut
        question_map = {
            Q("custom_contact.email_kyc_survey").id: "email",
            Q("custom_contact.point_of_contact_kyc_survey").id: "point_of_contact",
            Q("custom_contact.business_name_kyc_survey").id: "business_legal_name",
            Q("custom_contact.business_trade_name_kyc_survey").id: "business_trade_name",
            Q("custom_contact.business_constitution_kyc_survey").id: "const_business",
            Q("custom_contact.gst_no_kyc_survey").id: "gst_no",
            Q("custom_contact.udyam_certificate_kyc_survey").id: "udyam_number",
            Q("custom_contact.gst_duration_kyc_survey").id: "gst_return_duration",
            Q("custom_contact.gst_certificate_kyc_survey").id: "gst_certificate",
            Q("custom_contact.udyam_document_kyc_survey").id: "udyam_document",
            Q("custom_contact.shop_photos_kyc_survey").id: "shop_photos",
            Q("custom_contact.shop_videos_kyc_survey").id: "shop_videos",
            Q("custom_contact.matrix_bank_address_kyc_survey").id: "bank_detail",
            Q("custom_contact.matrix_director_detail_kyc_survey").id: "directors_detail",
            Q("custom_contact.matrix_address_detail_kyc_survey").id: "address_detail",
        }

        values = {}
        for line in self.user_input_line_ids:
            field_name = question_map.get(line.question_id.id)
            if not field_name:
                continue

            qtype = line.question_id.question_type

            if qtype in ("char_box", "text_box"):
                values[field_name] = line.value_char_box

            elif qtype == "simple_choice":
                if line.suggested_answer_id:
                    values[field_name] = line.suggested_answer_id.value
                elif line.value_char_box:
                    values[field_name] = line.value_char_box

            elif qtype == "multiple_choice":
                keys = line.suggested_answer_ids.mapped("value")
                if keys:
                    values[field_name] = ",".join(keys)
                elif line.value_char_box:
                    values[field_name] = line.value_char_box

            elif qtype == "upload_file":
                files = line.value_file_data_ids
                if not files:
                    continue
                if not line.question_id.upload_multiple_file:
                    values[field_name] = files[0].datas
                else:
                    values[field_name] = [(6, 0, files.ids)]

            elif qtype == "matrix":
                matrix_lines = self.user_input_line_ids.filtered(
                    lambda l: l.question_id.id == line.question_id.id and l.matrix_row_id and l.answer_type
                )

                row_data_map = {}
                for ml in matrix_lines:
                    row_key = ml.matrix_row_id.id
                    col_key = ml.suggested_answer_id.value if ml.suggested_answer_id else ml.answer_id.value
                    if not col_key:
                        continue

                    if row_key not in row_data_map:
                        row_data_map[row_key] = {}

                    value_field = f"value_{ml.answer_type}"
                    value = getattr(ml, value_field, None)
                    if isinstance(value, models.BaseModel):
                        value = value.id
                    row_data_map[row_key][col_key] = value

                if line.question_id.id == Q("custom_contact.matrix_bank_address_kyc_survey").id:
                    bank_details = []

                    for row in row_data_map.values():
                        attachments = []
                        cheque_data = row.get('Cancelled Cheque')
                        if cheque_data:
                            attachment = self.env['ir.attachment'].create({
                                'name': 'Cancelled Cheque',
                                'type': 'binary',
                                'datas': cheque_data,
                                'res_model': 'bank.details',
                                'res_id': 0,  # temp dummy ID
                            })
                            attachments.append(attachment.id)

                        bank_details.append((0, 0, {
                            'bank_name': row.get('Bank Name'),
                            'account_no': row.get('Account Number'),
                            'ifsc_code': row.get('IFSC Code'),
                            'bank_address': row.get('Bank Address'),
                            'bank_cheque_attachments': [(6, 0, attachments)] if attachments else False,
                        }))

                    values['bank_detail'] = bank_details

                elif line.question_id.id == Q("custom_contact.matrix_director_detail_kyc_survey").id:
                    values['directors_detail'] = [(0, 0, {
                        'designation': row.get('Designation'),
                        'contact_no': row.get('Contact Number'),
                        'email': row.get('Email Address'),
                        'aadhaar_card': row.get('Aadhaar Card'),
                        'pan_card': row.get('PAN Card'),
                    }) for row in row_data_map.values()]

                elif line.question_id.id == Q("custom_contact.matrix_address_detail_kyc_survey").id:
                    values['address_detail'] = [(0, 0, {
                        'business_street': row.get('Address'),
                        'business_city': row.get('City'),
                        'business_pincode': row.get('Pincode'),
                        'business_phone': row.get('Contact Number'),
                        'business_email': row.get('Email Address'),
                    }) for row in row_data_map.values()]

        if values:
            if self.partner_id:
                values['partner_id'] = self.partner_id.id
                res = self.env['res.partner.kyc.approval'].create(values)
                if res:
                    # Update attachments with correct res_id
                    for bank in res.bank_detail:
                        for attachment in bank.bank_cheque_attachments:
                            attachment.write({'res_id': bank.id})

                    self.partner_id.write({'is_kyc': True, 'rejection_date': False,
                                           'rejection_reason': False, 'is_rejected': False})
            elif self.email:
                partner = self.env['res.partner'].search([('email', '=', self.email)], limit=1)
                values['partner_id'] = partner.id
                res = self.env['res.partner.kyc.approval'].create(values)
                if res:
                    for bank in res.bank_detail:
                        for attachment in bank.bank_cheque_attachments:
                            attachment.write({'res_id': bank.id})

                    partner.write({'is_kyc': True, 'rejection_date': False,
                                   'rejection_reason': False, 'is_rejected': False})




