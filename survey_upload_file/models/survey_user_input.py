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
from odoo import models,_
from odoo.exceptions import UserError
import base64

class SurveyUserInput(models.Model):
    """
    This class extends the 'survey.user_input' model to add custom
    functionality for saving user answers.

    Methods:
        _save_lines: Save the user's answer for the given question
        _save_line_file:Save the user's file upload answer for the given
        question
        _get_line_answer_file_upload_values:
        Get the values to use when creating or updating a user input line
        for a file upload answer
    """
    _inherit = "survey.user_input"

    def _save_lines(self, question, answer, comment=None,
                    overwrite_existing=False):
        """Save the user's answer for the given question."""
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id), ])
        if question.question_type == 'upload_file':
            res = self._save_line_file(question, old_answers, answer)
        else:
            res = super()._save_lines(question, answer, comment, overwrite_existing)
        return res

    def _save_line_file(self, question, old_answers, answer):
        """
        Store files uploaded for an `upload_file` question.
        `answer` must be a tuple/list →  ([base64_1, base64_2 …], [name1, name2 …])
        """
        vals = self._get_line_answer_file_upload_values(question, answer)
        if old_answers:
            old_answers.write(vals)
            return old_answers
        return self.env['survey.user_input.line'].create(vals)

    def _get_line_answer_file_upload_values(self, question, answer):
        """
        Build vals for survey.user_input.line with attachments.
        Expected structure of `answer`:
            answer[0] → list of *base64 strings*
            answer[1] → list of filenames (same length)
        """
        datas_list, names_list = answer  # unpack

        # if not (isinstance(datas_list, list) and isinstance(names_list, list)):
        #     raise UserError("Invalid file upload payload.")
        #
        # if len(datas_list) != len(names_list):
        #     raise UserError("Mismatch between filenames and file data.")

        attachment_ids = []
        for datas_b64, fname in zip(datas_list, names_list):
            # sanity-check base64
            try:
                base64.b64decode(datas_b64, validate=True)
            except Exception as e:
                raise UserError(_(f"File '{fname}' is not valid base64: {e}"))

            attachment = self.env['ir.attachment'].create({
                'name': fname,
                'type': 'binary',
                'datas': datas_b64,
                'res_model': 'survey.user_input',
                'res_id': self.id,
            })
            attachment_ids.append(attachment.id)

        return {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': 'upload_file',
            # many2many or o2m depending on your line model
            'value_file_data_ids': [(6, 0, attachment_ids)],
        }

