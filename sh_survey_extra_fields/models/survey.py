# Part of Softhealer Technologies.

from urllib import parse
import base64
import datetime
import logging
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError
email_validator = re.compile(r"[^@]+@[^@]+\.[^@]+")
_logger = logging.getLogger(__name__)
from odoo.tools.translate import _  # Add this inside the method to

class SurveyQuestion(models.Model):
    _inherit = 'survey.question'
    _description = 'Inherit Survey Question for extra fields'

    def _get_stats_summary_data(self, user_input_lines):
        stats = {}
        if self.question_type in ['simple_choice', 'multiple_choice', 'que_sh_many2one', 'que_sh_many2many']:
            stats.update(self._get_stats_summary_data_choice(user_input_lines))
        elif self.question_type == 'numerical_box':
            stats.update(
                self._get_stats_summary_data_numerical(user_input_lines))

        if self.question_type in ['numerical_box', 'date', 'datetime']:
            stats.update(self._get_stats_summary_data_scored(user_input_lines))
        return stats

    def _get_stats_data(self, user_input_lines):
        if self.question_type == 'simple_choice':
            return self._get_stats_data_answers(user_input_lines)
        elif self.question_type == 'que_sh_many2one':
            return self._get_stats_data_answers(user_input_lines)
        elif self.question_type == 'que_sh_many2many':
            table_data, graph_data = self._get_stats_data_answers(
                user_input_lines)
            return table_data, [{'key': self.title, 'values': graph_data}]

        elif self.question_type == 'multiple_choice':
            table_data, graph_data = self._get_stats_data_answers(
                user_input_lines)
            return table_data, [{'key': self.title, 'values': graph_data}]
        elif self.question_type == 'matrix':
            return self._get_stats_graph_data_matrix(user_input_lines)
        return [line for line in user_input_lines], []
    validation_sh_time_min = fields.Char('Minimum Time')
    validation_sh_time_max = fields.Char('Maximum Time')
    validation_sh_time_step = fields.Integer('Time Step', default=60)

    validation_sh_range_min = fields.Integer('Minimum Range')
    validation_sh_range_max = fields.Integer('Maximum Range')
    validation_sh_range_step = fields.Integer('Range Step')

    validation_sh_week_min = fields.Char('Minimum Week')
    validation_sh_week_max = fields.Char('Maximum Week')
    validation_sh_week_step = fields.Integer('Week Step', default=1)

    validation_sh_month_min = fields.Char('Minimum Month')
    validation_sh_month_max = fields.Char('Maximum Month')
    validation_sh_month_step = fields.Integer('Month Step', default=1)

    validation_sh_password_minlen = fields.Integer('Password Minimum Length')
    validation_sh_password_maxlen = fields.Integer('Password Maximum Length')

    # for pattern in odoo standard textbox
    validation_is_sh_textbox_pattern = fields.Boolean(
        'Input must be in specified pattern')
    validation_sh_textbox_pattern = fields.Char('Textbox Pattern')
    validation_sh_textbox_placeholder = fields.Char('Textbox Placeholder')

    que_sh_many2one_model_id = fields.Many2one(
        comodel_name="ir.model", string="Model ")

    que_sh_many2many_model_id = fields.Many2one(
        comodel_name="ir.model", string="Model")

    # address fields
    sh_is_show_street = fields.Boolean(
        string="Show Street Field?", default=False)
    sh_is_show_street2 = fields.Boolean(
        string="Show Street2 Field?", default=False)
    sh_is_show_zip = fields.Boolean(string="Show Zip Field?", default=False)
    sh_is_show_city = fields.Boolean(string="Show City Field?", default=False)
    sh_is_show_state_id = fields.Boolean(
        string="Show State Field?", default=False)
    sh_is_show_country_id = fields.Boolean(
        string="Show Country Field?", default=False)

    # address fields labels
    sh_is_show_street_label = fields.Char(
        string='Street Label',
        default='Street',
        translate=True
    )
    sh_is_show_street2_label = fields.Char(
        string='Street 2 Label',
        default='Street 2',
        translate=True
    )
    sh_is_show_zip_label = fields.Char(
        string='Zip Label',
        default='Zip',
        translate=True
    )
    sh_is_show_city_label = fields.Char(
        string='City Label',
        default='City',
        translate=True
    )
    sh_is_show_country_id_label = fields.Char(
        string='Country Label',
        default='Country',
        translate=True
    )
    sh_is_show_state_id_label = fields.Char(
        string='State Label',
        default='State',
        translate=True
    )
    

    question_type = fields.Selection(selection_add=[
        ('que_sh_color', 'Color'),
        ('que_sh_email', 'E-mail'),
        ('que_sh_url', 'URL'),
        ('que_sh_time', 'Time'),
        ('que_sh_range', 'Range'),
        ('que_sh_week', 'Week'),
        ('que_sh_month', 'Month'),
        ('que_sh_password', 'Password'),
        ('que_sh_file', 'File'),
        ('que_sh_signature', 'Signature'),
        ('que_sh_many2one', 'Many2one'),
        ('que_sh_many2many', 'Many2many'),
        ('que_sh_address', 'Address'),
    ])
    upload_multiple_file = fields.Boolean(string='Upload Multiple File',
                                          help='Check this box if you want to '
                                               'allow users to upload '
                                               'multiple files')
    # ------------------------------------------------------------
    # VALIDATION
    # ------------------------------------------------------------

    def validate_question(self, answer, comment=None):

        """ Validate question, depending on question type and parameters
         for simple choice, text, date and number, answer is simply the answer of the question.
         For other multiple choices questions, answer is a list of answers (the selected choices
         or a list of selected answers per question -for matrix type-):
            - Simple answer : answer = 'example' or 2 or question_answer_id or 2019/10/10
            - Multiple choice : answer = [question_answer_id1, question_answer_id2, question_answer_id3]
            - Matrix: answer = { 'rowId1' : [colId1, colId2,...], 'rowId2' : [colId1, colId3, ...] }

         return dict {question.id (int): error (str)} -> empty dict if no validation error.
         """
        self.ensure_one()
        if isinstance(answer, str):
            answer = answer.strip()
        # Empty answer to mandatory question
        if self.constr_mandatory and not answer and self.question_type not in ['simple_choice', 'multiple_choice']:
            return {self.id: self.constr_error_msg or _('This question requires an answer.')}

        # because in choices question types, comment can count as answer
        if answer or self.question_type in ['simple_choice', 'multiple_choice']:
            if self.question_type == 'char_box':
                return self._validate_char_box(answer)
            elif self.question_type == 'numerical_box':
                return self._validate_numerical_box(answer)
            elif self.question_type in ['date', 'datetime']:
                return self._validate_date(answer)
            elif self.question_type in ['simple_choice', 'multiple_choice']:
                return self._validate_choice(answer, comment)
            elif self.question_type == 'matrix':
                return self._validate_matrix(answer)
            elif self.question_type == 'que_sh_color':
                return self.validate_que_sh_color(answer)
            elif self.question_type == 'que_sh_email':
                return self.validate_que_sh_email(answer)
            elif self.question_type == 'que_sh_url':
                return self.validate_que_sh_url(answer)
            elif self.question_type == 'que_sh_time':
                return self.validate_que_sh_time(answer)
            elif self.question_type == 'que_sh_range':
                return self.validate_que_sh_range(answer)
            elif self.question_type == 'que_sh_week':
                return self.validate_que_sh_week(answer)
            elif self.question_type == 'que_sh_month':
                return self.validate_que_sh_month(answer)
            elif self.question_type == 'que_sh_password':
                return self.validate_que_sh_password(answer)
            elif self.question_type == 'que_sh_file':
                return self.validate_que_sh_file(answer)
            elif self.question_type == 'que_sh_signature':
                return self.validate_que_sh_signature(answer)
            elif self.question_type == 'que_sh_many2one':
                return self.validate_que_sh_many2one(answer)
            elif self.question_type == 'que_sh_many2many':
                return self.validate_que_sh_many2many(answer)
            elif self.question_type == 'que_sh_address':
                return self.validate_que_sh_address(answer)
        return {}

    # ====================================================================
    # for color field.
    # ====================================================================

    def validate_que_sh_color(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for email field.
    # ====================================================================

    def validate_que_sh_email(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for url field.
    # ====================================================================

    def validate_que_sh_url(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for time field.
    # ====================================================================
    def _validate_matrix(self, answers):
        """
        Custom matrix validation by Softhealer Technologies.
        Includes format checks and duplicate detection for emails and mobile numbers across rows.
        """
        import re
        from odoo.tools.translate import _

        def is_valid_email(val):
            return bool(re.fullmatch(r"[^@]+@[^@]+\.[^@]+", val))

        def is_valid_mobile(val):
            return bool(re.fullmatch(r"^[6-9]\d{9}$", val))

        def is_valid_pincode(val):
            return bool(re.fullmatch(r"^\d{6}$", val))

        def is_valid_account_number(val):
            return bool(re.fullmatch(r"\d{9,18}", val))

        def is_valid_ifsc(val):
            return bool(re.fullmatch(r"^[A-Z]{4}0[A-Z0-9]{6}$", val))

        # --------------------------
        # Track duplicates per row
        # --------------------------
        seen_emails = {}
        seen_contacts = {}

        for key, value_list in answers.items():
            if "_" not in key or key.startswith("rowcount"):
                continue  # skip invalid or extra keys
            row_id, answer_id = key.split('_')
            answer = self.env['survey.question.answer'].browse(int(answer_id))

            for val in value_list:
                if not val:
                    continue

                if answer.sh_value_type == 'textbox':
                    if answer.is_email:
                        lower_email = val.strip().lower()
                        if lower_email in seen_emails and seen_emails[lower_email] != row_id:
                            return {
                                self.id: _(
                                    "Duplicate Email found in multiple rows: '%s'. Must be unique across rows.") % val
                            }
                        seen_emails[lower_email] = row_id
                        if not is_valid_email(val):
                            return {
                                self.id: _("Invalid Email in '%s' → '%s'. Example: user@example.com") % (answer.value,
                                                                                                         val)
                            }

                    if answer.is_mobile:
                        clean_mobile = val.strip()
                        if clean_mobile in seen_contacts and seen_contacts[clean_mobile] != row_id:
                            return {
                                self.id: _(
                                    "Duplicate Contact Number in multiple rows: '%s'. Must be unique across rows.") % val
                            }
                        seen_contacts[clean_mobile] = row_id
                        if not is_valid_mobile(val):
                            return {
                                self.id: _(
                                    "Invalid Mobile Number in '%s' → '%s'. Must be 10 digits, start with 6-9") % (
                                             answer.value, val)
                            }

                    if answer.is_pincode and not is_valid_pincode(val):
                        return {
                            self.id: _("Invalid Pincode in '%s' → '%s'. Must be exactly 6 digits") % (answer.value, val)
                        }

                    if answer.is_acc_no and not is_valid_account_number(val):
                        return {
                            self.id: _("Invalid Account Number in '%s' → '%s'. Must be 9-18 digits") % (answer.value,
                                                                                                        val)
                        }

                    if answer.is_ifsc and not is_valid_ifsc(val.upper()):
                        return {
                            self.id: _(
                                "Invalid IFSC Code in '%s' → '%s'. Format: 4 letters + 0 + 6 alphanumeric (e.g., SBIN0001234)") % (
                                         answer.value, val)
                        }

        # --------------------------
        # Check mandatory constraints
        # --------------------------
        if self.add_an_item and self.matrix_subtype == 'sh_custom_matrix' and self.constr_mandatory:
            row_answers = {str(row_id): [] for row_id in self.matrix_row_ids.ids}
            for key, value in answers.items():
                if "_" not in key or key.startswith("rowcount"):
                    continue  # skip invalid or extra keys
                row_id, _ = key.split('_')
                valid_answers = [ans for ans in value]
                row_answers[row_id].extend(valid_answers)
            filled_ans = []
            for row, ans in row_answers.items():
                if not all(ans):
                    filled_ans.append(False)
                else:
                    filled_ans.append(True)
            if True not in filled_ans:
                return {self.id: self.constr_error_msg or 'This question requires an answer.'}

        if not self.add_an_item and self.constr_mandatory:
            for row in answers:
                if answers[row] == ['']:
                    return {self.id: self.constr_error_msg or 'This question requires an answer.'}

        return {}

    # def _validate_matrix(self, answers):
    #     print("\n _validate_matrix 1 >", answers)
    #     print("\n _self.matrix_row_ids >", self.matrix_row_ids )
    #     print("\n len(self.matrix_row_ids) >", len(self.matrix_row_ids) )
    #     print("\n len(answers) >", len(answers) )
    #     # Validate that each line has been answered
    #     if self.constr_mandatory and len(self.matrix_row_ids) != len(answers):
    #         print("\n _validate_matrix 2 >")

    #         return {self.id: self.constr_error_msg or _('This question requires an answer.')}
    #     return {}
    


    def validate_que_sh_time(self, answer):
        isData = self.question_type == 'que_sh_time'
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        if self.validation_required:
            # Check if answer is in the right range
            if isData:
                min_date = datetime.datetime.strptime(
                    self.validation_sh_time_min, '%H:%M')
                max_date = datetime.datetime.strptime(
                    self.validation_sh_time_max, '%H:%M')
                answer = datetime.datetime.strptime(answer, '%H:%M')
                if answer < min_date or answer > max_date:
                    return {self.id: self.validation_error_msg}

        return {}

    # ====================================================================
    # for Range field.
    # ====================================================================

    def validate_que_sh_range(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for Week field.
    # ====================================================================

    def validate_que_sh_week(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for Month field.
    # ====================================================================

    def validate_que_sh_month(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for Password field.
    # ====================================================================

    def validate_que_sh_password(self, answer):
        isData = self.question_type == 'que_sh_password'
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        if self.validation_required:
            # Check if answer is in the right range
            if isData:
                minlen = self.validation_sh_password_minlen
                maxlen = self.validation_sh_password_maxlen
                if len(answer) < minlen or len(answer) > maxlen:
                    return {self.id: self.validation_error_msg}
        return {}

    # ====================================================================
    # for File field.
    # ====================================================================
    def validate_que_sh_file(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for Signature Field.
    # ====================================================================

    def validate_que_sh_signature(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for Many2one Field.
    # ====================================================================
    def validate_que_sh_many2one(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for Many2many Field.
    # ====================================================================

    def validate_que_sh_many2many(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}

    # ====================================================================
    # for Address Field.
    # ====================================================================
    def validate_que_sh_address(self, answer):
        if self.constr_mandatory and not answer:
            return {self.id: self.constr_error_msg}
        return {}


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def _save_lines(self, question, answer, comment=None, overwrite_existing=True):
        """ Save answers to questions, depending on question type

            If an answer already exists for question and user_input_id, it will be
            overwritten (or deleted for 'choice' questions) (in order to maintain data consistency).
        """
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)
        ])
        if old_answers and not overwrite_existing:
            raise UserError(_("This answer cannot be overwritten."))

        if question.question_type in ['char_box', 'text_box', 'numerical_box', 'date', 'datetime']:
            self._save_line_simple_answer(question, old_answers, answer)
            if question.save_as_email and answer:
                self.write({'email': answer})
            if question.save_as_nickname and answer:
                self.write({'nickname': answer})

        elif question.question_type in ['simple_choice', 'multiple_choice']:
            self._save_line_choice(question, old_answers, answer, comment)
        elif question.question_type == 'matrix':
            self._save_line_matrix(question, old_answers, answer, comment)
        elif question.question_type in ['que_sh_color']:
            self.save_line_que_sh_field(
                question, old_answers, answer, 'ans_sh_color')
        elif question.question_type in ['que_sh_email']:
            self.save_line_que_sh_field(
                question, old_answers, answer, 'ans_sh_email')
        elif question.question_type in ['que_sh_url']:
            self.save_line_que_sh_field(
                question, old_answers, answer, 'ans_sh_url')
        elif question.question_type in ['que_sh_time']:
            self.save_line_que_sh_field(
                question, old_answers, answer, 'ans_sh_time')
        elif question.question_type in ['que_sh_range']:
            self.save_line_que_sh_field(
                question, old_answers, answer, 'ans_sh_range')
        elif question.question_type in ['que_sh_week']:
            self.save_line_que_sh_field(
                question, old_answers, answer, 'ans_sh_week')
        elif question.question_type in ['que_sh_month']:
            self.save_line_que_sh_field(
                question, old_answers, answer, 'ans_sh_month')
        elif question.question_type in ['que_sh_password']:
            self.save_line_que_sh_field(
                question, old_answers, answer, 'ans_sh_password')
        elif question.question_type in ['que_sh_file']:
            self.save_line_que_sh_file(
                question, old_answers, answer, 'ans_sh_file')
        elif question.question_type in ['que_sh_signature']:
            self.save_line_que_sh_signature(
                question, old_answers, answer, 'ans_sh_signature')
        elif question.question_type in ['que_sh_address']:
            self.save_line_que_sh_address(
                question, old_answers, answer, 'ans_sh_address')

        elif question.question_type in ['que_sh_many2one']:
            self.save_line_que_sh_many2one(
                question, old_answers, answer, 'ans_sh_many2one')

        elif question.question_type in ['que_sh_many2many']:
            self.save_line_que_sh_many2many(
                question, old_answers, answer, 'ans_sh_many2many')

        else:
            raise AttributeError(question.question_type +
                                 ": This type of question has no saving function")

    # ====================================================================
    # for color field.
    # ====================================================================

    @api.model
    def save_line_que_sh_field(self, question, old_answers, answer, answer_type):
        vals_list = []

        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }
        if not answer or (isinstance(answer, str) and not answer.strip()):
            vals.update(answer_type=None, skipped=True)
            return vals
        vals['value_%s' % answer_type] = answer
        vals_list.append(vals)
        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)

    @api.model
    def save_line_que_sh_file(self, question, old_answers, answer, answer_type):
        file_list = answer
        
        if isinstance(answer, dict):
            file_list = [answer]
        vals_list = []
        for file_dict in file_list:
            
            datas = file_dict.get('datas')
            if datas:
                vals = self._get_line_answer_values(
                    question, datas, answer_type)
                vals.update({
                    'value_ans_sh_file_fname': file_dict.get("fname"),
                    })
                vals_list.append(vals)
            
        if not vals_list:
            vals = self._get_line_answer_values(question, "", answer_type)
            vals.update(answer_type=None, skipped=True)
            vals_list.append(vals)
        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)

    @api.model
    def save_line_que_sh_signature(self, question, old_answers, answer, answer_type):
        vals_list = []
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
            'value_ans_sh_signature': answer,
            'value_ans_sh_signature_src': answer,

        }
        if not answer or (isinstance(answer, str) and not answer.strip()):
            vals.update(answer_type=None, skipped=True)
            return vals
        vals['value_%s' % answer_type] = answer
        vals_list.append(vals)
        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)

    # ------------------------------
    # Address Fields.
    # ------------------------------
    @api.model
    def save_line_que_sh_address(self, question, old_answers, answer, answer_type):
        vals_list = []
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': answer_type,
        }
        if not answer or (isinstance(answer, str) and not answer.strip()):
            vals.update(answer_type=None, skipped=True)
            return vals
        # Add individual address fields in vals here
        query_dict = dict(parse.parse_qsl(answer)) or {}
        vals["value_ans_sh_street"] = query_dict.get('street', False)
        vals["value_ans_sh_street2"] = query_dict.get('street2', False)
        vals["value_ans_sh_city"] = query_dict.get('city', False)
        vals["value_ans_sh_zip"] = query_dict.get('zip', False)
        vals["value_ans_sh_state_id"] = query_dict.get('state_id', False)
        vals["value_ans_sh_country_id"] = query_dict.get('country_id', False)
        # TO AVOID ERROR BELOW IS NECESSARY
        street = query_dict.get('street', '')
        street2 = query_dict.get('street2', '')
        city = query_dict.get('city', '')
        zip = query_dict.get('zip', '')
        state_id = query_dict.get('state_id', '')
        country_id = query_dict.get('country_id', '')

        if street:
            street += ' '
        if street2:
            street2 += ' '
        if city:
            city += ' '
        if zip:
            zip += ' '
        if state_id:
            integer_state_id = state_id
            if type(state_id) != int:
                integer_state_id = int(state_id)
            state = self.env["res.country.state"].sudo().browse([
                integer_state_id])
            if state:
                state_id = state.name

            state_id += ' '
        if country_id:

            integer_country_id = country_id
            if type(country_id) != int:
                integer_country_id = int(country_id)

            country = self.env["res.country"].sudo().browse(
                [integer_country_id])
            if country:
                country_id = country.name

            country_id += ' '

        complete_address = street + street2 + city + zip + state_id + country_id
        vals["value_ans_sh_address"] = complete_address or False
        vals_list.append(vals)
        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)

    @api.model
    def save_line_que_sh_many2one(self, question, old_answers, answer, answer_type):
        vals_list = []
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'skipped': False,
            'answer_type': 'suggestion',
        }
        if not answer or (isinstance(answer, str) and not answer.strip()):
            vals.update(answer_type=None, skipped=True)
            return vals

        # ---------------------------------------------------------------
        # To Make Many2one fields like Multiple Choice only one answer.
        suggested_answer = self.env["survey.question.answer"].search([
            ('question_id', '=', question.id),
            ('value', '=', answer),
        ], limit=1)

        if not suggested_answer:
            suggested_answer = self.env["survey.question.answer"].create({
                'question_id': question.id,
                'value': answer,
            })
        if suggested_answer:
            vals['suggested_answer_id'] = suggested_answer.id

        # To Make Many2one fields like Multiple Choice only one answer.
        # ---------------------------------------------------------------
        vals_list.append(vals)
        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)

    @api.model
    def save_line_que_sh_many2many(self, question, old_answers, answers, answer_type):
        vals_list = []
        if not (isinstance(answers, list)):
            answers = [answers]
        for answer in answers:
            vals = {
                'user_input_id': self.id,
                'question_id': question.id,
                'skipped': False,
                'answer_type': 'suggestion',
            }
            if not answer or (isinstance(answer, str) and not answer.strip()):
                vals.update(answer_type=None, skipped=True)
                return vals

        # ---------------------------------------------------------------
        # To Make Many2one fields like Multiple Choice only one answer.
            suggested_answer = self.env["survey.question.answer"].search([
                ('question_id', '=', question.id),
                ('value', '=', answer),
            ], limit=1)

            if not suggested_answer:
                suggested_answer = self.env["survey.question.answer"].create({
                    'question_id': question.id,
                    'value': answer,
                })
            if suggested_answer:
                vals['suggested_answer_id'] = suggested_answer.id

        # To Make Many2one fields like Multiple Choice only one answer.
        # ---------------------------------------------------------------
            vals_list.append(vals)
        old_answers.sudo().unlink()
        return self.env['survey.user_input.line'].create(vals_list)


class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'
    _description = 'Survey User Input Line for extra fields'

    value_ans_sh_color = fields.Char(string="Color")
    value_ans_sh_email = fields.Char(string="E-mail")
    value_ans_sh_url = fields.Char(string="URL")
    value_ans_sh_time = fields.Char(string="Time")
    value_ans_sh_range = fields.Integer(string="Range")
    value_ans_sh_week = fields.Char(string="Week")
    value_ans_sh_month = fields.Char(string="Month")
    value_ans_sh_password = fields.Char(string="Password")
    value_ans_sh_file = fields.Binary(string="File")
    value_ans_sh_file_fname = fields.Char(string="File Name")
    value_ans_sh_signature = fields.Binary(string="Signature")
    value_ans_sh_signature_src = fields.Text(string="Signature src")

    value_ans_sh_many2one = fields.Char(string="Many2one")
    value_ans_sh_many2many = fields.Char(string="Many2many")

    # address fields
    value_ans_sh_street = fields.Char()
    value_ans_sh_street2 = fields.Char()
    value_ans_sh_zip = fields.Char()
    value_ans_sh_city = fields.Char()
    value_ans_sh_state_id = fields.Many2one(
        "res.country.state", string='State')
    value_ans_sh_country_id = fields.Many2one('res.country', string='Country')
    value_ans_sh_address = fields.Text(string="Address")

    


    answer_type = fields.Selection(selection_add=[
        ('ans_sh_color', 'Color'),
        ('ans_sh_email', 'E-mail'),
        ('ans_sh_url', 'URL'),
        ('ans_sh_time', 'Time'),
        ('ans_sh_range', 'Range'),
        ('ans_sh_week', 'Week'),
        ('ans_sh_month', 'Month'),
        ('ans_sh_password', 'Password'),
        ('ans_sh_file', 'File'),
        ('ans_sh_signature', 'Signature'),
        ('ans_sh_many2one', 'Many2one'),
        ('ans_sh_many2many', 'Many2many'),
        ('ans_sh_address', 'Address'),
    ])

    access_token = fields.Char('Identification token',
                               related="user_input_id.access_token",
                               readonly=False, store=True)
