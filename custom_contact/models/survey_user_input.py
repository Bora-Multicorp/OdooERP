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
        # Map question IDs to partner field names
        question_map = {
            # Basic text/char fields
            Q("custom_contact.email_kyc_survey").id: "email",
            Q("custom_contact.point_of_contact_kyc_survey").id: "point_of_contact",
            Q("custom_contact.business_name_kyc_survey").id: "business_legal_name",
            Q("custom_contact.business_trade_name_kyc_survey").id: "business_trade_name",
            # Q("custom_contact.business_address_kyc_survey").id: "business_street",
            # Q("custom_contact.business_city_kyc_survey").id: "business_city",
            # Q("custom_contact.business_pincode_kyc_survey").id: "business_pincode",
            # Q("custom_contact.additional_address_kyc_survey").id: "additional_street",
            # Q("custom_contact.additional_city_kyc_survey").id: "additional_city",
            # Q("custom_contact.additional_pincode_kyc_survey").id: "additional_zip",
            # Q("custom_contact.additional_contact_no_kyc_survey").id: "additional_phone",
            # Q("custom_contact.additional_email_kyc_survey").id: "additional_email",
            Q("custom_contact.business_constitution_kyc_survey").id: "const_business",
            Q("custom_contact.director_name_kyc_survey").id: "director_name",
            Q("custom_contact.director_contact_no_kyc_survey").id: "director_phone",
            Q("custom_contact.director_email_kyc_survey").id: "director_email",
            Q("custom_contact.gst_no_kyc_survey").id: "gst_no",
            Q("custom_contact.udyam_certificate_kyc_survey").id: "udyam_number",
            Q("custom_contact.gst_duration_kyc_survey").id: "gst_return_duration",
            # Q("custom_contact.bank_name_kyc_survey").id: "bank_name",
            # Q("custom_contact.account_no_kyc_survey").id: "account_no",
            # Q("custom_contact.ifsc_code_kyc_survey").id: "ifsc_code",
            # Q("custom_contact.bank_address_kyc_survey").id: "bank_address",

            # File uploads
            Q("custom_contact.aadhaar_card_kyc_survey").id: "aadhaar_card",
            Q("custom_contact.pan_card_kyc_survey").id: "pan_card",
            Q("custom_contact.gst_certificate_kyc_survey").id: "gst_certificate",
            Q("custom_contact.udyam_document_kyc_survey").id: "udyam_document",
            Q("custom_contact.shop_photos_kyc_survey").id: "shop_photos",
            Q("custom_contact.shop_videos_kyc_survey").id: "shop_videos",
            #Q("custom_contact.cancel_cheque_kyc_survey").id: "bank_cheque_attachments",
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
                # self.partner_id.write(values)
                values['partner_id'] = self.partner_id.id
                res = self.env['res.partner.kyc.approval'].create(values)
                if res:
                    self.partner_id.write({'is_kyc': True, 'rejection_date': False,
                                           'rejection_reason': False,
                                           'is_rejected': False, })
            elif self.email:
                partner = self.env['res.partner'].search([('email', '=', self.email)], limit=1)

                # partner.write(values)
                values['partner_id'] = partner.id
                res = self.env['res.partner.kyc.approval'].create(values)
                if res:
                    partner.write({'is_kyc': True, 'rejection_date': False,
                                   'rejection_reason': False,
                                   'is_rejected': False, })
