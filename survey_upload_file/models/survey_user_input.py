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
from odoo import models, _, fields
from odoo.exceptions import UserError
import base64
import binascii

class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    def _save_lines(self, question, answer, comment=None, overwrite_existing=True):
        """Extended to handle 'upload_file' in addition to all standard types."""
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)
        ])

        if old_answers and not overwrite_existing:
            raise UserError(_("This answer cannot be overwritten."))

        if question.question_type == 'upload_file':
            self._save_line_file_upload(question, old_answers, answer)

        elif question.question_type in ['char_box', 'text_box', 'scale', 'numerical_box', 'date', 'datetime']:
            self._save_line_simple_answer(question, old_answers, answer)
            if question.save_as_email and answer:
                self.write({'email': answer})
            if question.save_as_nickname and answer:
                self.write({'nickname': answer})

        elif question.question_type in ['simple_choice', 'multiple_choice']:
            self._save_line_choice(question, old_answers, answer, comment)

        elif question.question_type == 'matrix':
            self._save_line_matrix(question, old_answers, answer, comment)

        # else:
        #     raise AttributeError(question.question_type + ": This type of question has no saving function")

    def _save_line_file_upload(self, question, old_answers, answer):
        """Save a file upload answer (custom 'upload_file' type)."""
        vals = self._get_line_answer_file_upload_values(question, 'upload_file', answer)
        if old_answers:
            old_answers.write(vals)
        else:
            self.env['survey.user_input.line'].create(vals)

    def _get_line_answer_file_upload_values(self, question, answer_type, answer):
        """Prepare values for a user input line with file uploads."""
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }

        if answer_type == 'upload_file':
            if not answer or not isinstance(answer, (list, tuple)) or len(answer) < 2:
                return vals

            file_data = answer[0]
            file_name = answer[1]

            if isinstance(file_data, str):
                file_data = [file_data]
            if isinstance(file_name, str):
                file_name = [file_name]

            attachment_ids = []
            for data, name in zip(file_data, file_name):
                if not self._is_valid_base64(data):
                    continue
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

