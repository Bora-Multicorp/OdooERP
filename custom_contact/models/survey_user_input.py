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
            "survey_upload_file.vendor_kyc_form_survey", raise_if_not_found=False
        )
        if not vendor_survey or self.survey_id != vendor_survey:
            return  # We only process the vendor KYC form

        Q = self.env.ref  # shortcut
        # Map question IDs to partner field names
        question_map = {
            # Basic text/char fields
            Q("survey_upload_file.email_kyc_survey").id: "email",
            Q("survey_upload_file.point_of_contact_kyc_survey").id: "point_of_contact",
            Q("survey_upload_file.business_name_kyc_survey").id: "business_legal_name",
            Q("survey_upload_file.business_trade_name_kyc_survey").id: "business_trade_name",
            Q("survey_upload_file.business_address_kyc_survey").id: "business_street",
            Q("survey_upload_file.business_city_kyc_survey").id: "business_city",
            Q("survey_upload_file.business_pincode_kyc_survey").id: "business_pincode",
            Q("survey_upload_file.additional_address_kyc_survey").id: "additional_street",
            Q("survey_upload_file.additional_city_kyc_survey").id: "additional_city",
            Q("survey_upload_file.additional_pincode_kyc_survey").id: "additional_zip",
            Q("survey_upload_file.additional_contact_no_kyc_survey").id: "additional_phone",
            Q("survey_upload_file.additional_email_kyc_survey").id: "additional_email",
            #Q("survey_upload_file.business_constitution_kyc_survey").id: "const_business",
            Q("survey_upload_file.director_name_kyc_survey").id: "director_name",
            Q("survey_upload_file.director_contact_no_kyc_survey").id: "director_phone",
            Q("survey_upload_file.director_email_kyc_survey").id: "director_email",
            Q("survey_upload_file.gst_no_kyc_survey").id: "gst_no",
            Q("survey_upload_file.udyam_certificate_kyc_survey").id: "udyam_number",
            Q("survey_upload_file.gst_duration_kyc_survey").id: "gst_return_duration",
            Q("survey_upload_file.bank_name_kyc_survey").id: "bank_name",
            Q("survey_upload_file.account_no_kyc_survey").id: "account_no",
            Q("survey_upload_file.ifsc_code_kyc_survey").id: "ifsc_code",
            Q("survey_upload_file.bank_address_kyc_survey").id: "bank_address",

            # File uploads
            Q("survey_upload_file.aadhaar_card_kyc_survey").id: "aadhaar_card",
            Q("survey_upload_file.pan_card_kyc_survey").id: "pan_card",
            Q("survey_upload_file.gst_certificate_kyc_survey").id: "gst_certificate",
            Q("survey_upload_file.udyam_document_kyc_survey").id: "udyam_document",
            Q("survey_upload_file.shop_photos_kyc_survey").id: "shop_photos",
            Q("survey_upload_file.shop_videos_kyc_survey").id: "shop_videos",
            Q("survey_upload_file.cancel_cheque_kyc_survey").id: "bank_cheque_attachments",
        }
        values = {}

        for line in self.user_input_line_ids:
            field_name = question_map.get(line.question_id.id)
            if not field_name:
                continue

            qtype = line.question_id.question_type

            # Text inputs
            if qtype in ("char_box", "text_box"):
                values[field_name] = line.value_char_box
            # Choice fields
            elif qtype == "simple_choice":
                # single-select radio
                if line.suggested_answer_id:
                    # technical key, e.g. "monthly"
                    values[field_name] = line.suggested_answer_id.value
                elif line.value_char_box:  # respondent typed “Other”
                    values[field_name] = line.value_char_box
            elif qtype == "multiple_choice":
                keys = line.suggested_answer_ids.mapped("value")  # ['key1', 'key2', ...]
                if keys:
                    # store as comma-separated string if partner field is Char,
                    # or convert to something else if you made gst_return_duration a many2many
                    values[field_name] = ",".join(keys)
                elif line.value_char_box:
                    values[field_name] = line.value_char_box

            # File uploads
            elif qtype == "upload_file":
                files = line.value_file_data_ids
                if not files:
                    continue
                # Store multiple file attachments, store as relationship
                if not line.question_id.upload_multiple_file:
                    # Single file upload (e.g., to Binary field)
                    values[field_name] = files[0].datas
                else:
                    # Multiple file upload (Many2many)
                    values[field_name] = [(6, 0, files.ids)]
        if values:
            if self.partner_id:
                #self.partner_id.write(values)
                values['partner_id'] = self.partner_id.id
                res = self.env['res.partner.kyc.approval'].create(values)
                if res:
                    self.partner_id.write({'is_kyc': True})
            elif self.email:
                partner = self.env['res.partner'].search([('email', '=', self.email)], limit=1)

                #partner.write(values)
                values['partner_id'] = partner.id
                res = self.env['res.partner.kyc.approval'].create(values)
                if res:
                    partner.write({'is_kyc': True})
