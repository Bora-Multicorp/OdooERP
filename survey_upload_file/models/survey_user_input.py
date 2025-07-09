# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Mohammed Dilshad Tk (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models
import base64
import binascii

class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def _save_lines(self, question, answer, comment=None, overwrite_existing=False):
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id),
        ])
        if question.question_type == 'upload_file':  # fix comparison logic
            res = self._save_line_simple_answer(question, old_answers, answer)
        else:
            res = super()._save_lines(question, answer, comment, overwrite_existing)
        return res

    def _save_line_simple_answer(self, question, old_answers, answer):
        vals = self._get_line_answer_file_upload_values(question, 'upload_file', answer)
        if old_answers:
            old_answers.write(vals)
            return old_answers
        else:
            return self.env['survey.user_input.line'].create(vals)

    def _get_line_answer_file_upload_values(self, question, answer_type, answer):
        """Get the values to use when creating or updating a user input line for a file upload answer."""
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }

        if answer_type == 'upload_file':
            if not answer or not isinstance(answer, (list, tuple)) or len(answer) < 2:
                # No valid file uploaded
                return vals

            file_data = answer[0]
            file_name = answer[1]

            # Normalize single value to list
            if isinstance(file_data, str):
                file_data = [file_data]
            if isinstance(file_name, str):
                file_name = [file_name]

            attachment_ids = []
            for data, name in zip(file_data, file_name):
                if not self._is_valid_base64(data):
                    continue  # or raise ValidationError(f"Invalid file format for {name}")
                attachment = self.env['ir.attachment'].create({
                    'name': name,
                    'type': 'binary',
                    'datas': data,
                    'res_model': 'survey.user_input',
                    'res_id': self.id,
                })
                attachment_ids.append(attachment.id)

            vals['value_file_data_ids'] = [(6, 0, attachment_ids)]

        return vals

    def _is_valid_base64(self, s):
        """Check if a string is valid base64."""
        try:
            if not s or not isinstance(s, str):
                return False
            base64.b64decode(s, validate=True)
            return True
        except (binascii.Error, ValueError, TypeError):
            return False


