/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import SurveyFormWidget from '@survey/js/survey_form';
import { rpc } from "@web/core/network/rpc";
import {
    deserializeDate,
    deserializeDateTime,
    parseDateTime,
    parseDate,
    serializeDateTime,
    serializeDate,
} from "@web/core/l10n/dates";


SurveyFormWidget.include({
    events: Object.assign({}, SurveyFormWidget.prototype.events || {}, {
        "change .js_cls_country_id": "_onChangeCountry",
        'change .sh_file_input': '_onChangeFileInput',
        "click .js_cls_sh_signature_clear_btn": "_onClickSignatureClearButton",
        'input input.o_survey_question_text_box': '_onLegalNameChangeInit',
        'blur input.o_survey_question_text_box[type="email"]': '_onChangeVendorEmailInput',
    }),

    VENDOR_EMAIL_NOT_FOUND: "This email is not registered in our system. Please enter a valid email or contact admin.",


    /**
     * @override
     */
    init: function () {
        this.SH_FILE_DATA_DICTIONARY = {};
        this._super.apply(this, arguments);
    },

    start: function () {
        var self = this;
        this.validatedEmails = {};
        return this._super.apply(this, arguments).then(function () {
            var $form = self.$('form');
            if (!$form.length) return;
            $form.find('[data-question-code="vendor_email"]').each(function () {
                var $input = $(this);
                var v_email = $input.val().trim();
                if (v_email) {
                    self._validateVendorEmail($input);
                }
            });
        });
    },

    _onInputRangeValueChange: function (ev) {
        var $input = $(ev.currentTarget);
        $input.next('label').html($input.val())
    },

    _onChangeVendorEmailInput: function(ev) {
        var $input = $(ev.currentTarget);
        var question_code = $input.data('question-code');
        console.log("Question code:", question_code);
        if (question_code === 'vendor_email') {
            this._validateVendorEmail($input);
        }
    },

    _clearError: function($questionWrapper) {
        $questionWrapper.find('.o_survey_question_error span').remove();
        $questionWrapper.find('.o_survey_question_error').removeClass('slide_in');
    },

    _validateVendorEmail: function($input) {
        var self = this;
        var email = $input.val().trim();
        var $questionWrapper = $input.closest(".js_question-wrapper");
        var questionId = $questionWrapper.attr('id');
        if (!self.validatedEmails) self.validatedEmails = {};
        self._clearError($questionWrapper);
        if (!email) {
            $input.removeClass('is-valid').addClass('is-invalid');
            self.validatedEmails[questionId] = true;
            var errors = {};
            errors[questionId] = "Email is required.";
            self._showErrors(errors);
            return false;
        }
        // RPC call to check email in res.partner
        rpc("/survey/check_vendor_email", {'vendor_email': email}).then(function(count) {
            var errors = {}; // reset errors here
            if (count > 0) {
                $input.removeClass('is-invalid').addClass('is-valid');
                self.validatedEmails[questionId] = true;
                self._clearError($questionWrapper);
            } else {
                $input.removeClass('is-valid').addClass('is-invalid');
                self.validatedEmails[questionId] = false;
                errors[questionId] = self.VENDOR_EMAIL_NOT_FOUND;
                self._showErrors(errors);
            }
         });
        return true;
    },

    /**
     * @private
     * @param {FileInputEvent} ev
     */
     _onChangeFileInput: async function (ev) {
    var self = this;
    var $fileUpload = $(ev.currentTarget);
    if (!$fileUpload.length) return;

    const imageTypes = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif', 'image/bmp', 'image/webp', 'image/svg+xml'];
    const videoTypes = ['video/mp4', 'video/mpeg', 'video/ogg', 'video/webm', 'video/avi', 'video/quicktime'];
    const pdfTypes = ['application/pdf'];
    const officeTypes = [
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    ];

    const FILE_LIST = [];
    const toBase64 = (file) => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
        reader.readAsDataURL(file);
    });

    const labelText = $fileUpload.closest('.js_question-wrapper')
        .find('.o_survey_question_title, h3 span')
        .first().text()
        .trim().toLowerCase();

    let matrixColumnLabel = '';
    try {
        const colIndex = $fileUpload.closest('td').index();
        matrixColumnLabel = $fileUpload.closest('table')
            .find('thead th').eq(colIndex).text()
            .trim().toLowerCase();
    } catch (e) {
        matrixColumnLabel = '';
    }

    // Normalize the key
    const rawKey = matrixColumnLabel || labelText;
    const sizeKey = rawKey.replace(/\s+/g, ' ').trim();

    const maxFilesPerField = {
        'shop photos': 10, //Upload up to 10 supported files: image. Max 100 MB per file
        'shop videos': 10, // Upload up to 10 supported files: video. Max 100 MB per file.
        'electricity bill': 5, // Upload up to 5 supported files. Max 10 MB per file.
        'moa or aoa': 5, // Upload up to 5 supported files. Max 10 MB per file.
    };

    const sizeLimits = {
        'aadhaar card': 10 * 1024 * 1024,
        'pan card': 10 * 1024 * 1024,
        'pan card document(company)': 10 * 1024 * 1024,
        'partnership deed or llp deed': 10 * 1024 * 1024,
        'gst certificate': 10 * 1024 * 1024,
        'udyam documents': 10 * 1024 * 1024,
        'shop act documents': 10 * 1024 * 1024,
        'shop photos': 100 * 1024 * 1024,
        'shop videos': 100 * 1024 * 1024,
        'incorporation certificate': 100 * 1024 * 1024,
        'moa or aoa': 10 * 1024 * 1024,
        'electricity bill': 10 * 1024 * 1024,
        'cancelled cheque': 10 * 1024 * 1024,
    };

    const perFileLimits = { // per file size
        'shop photos': 100 * 1024 * 1024,
        'shop videos': 100 * 1024 * 1024,
        'electricity bill': 10 * 1024 * 1024,
        'moa or aoa': 10 * 1024 * 1024,
    };

    const maxSizePerField = sizeLimits[sizeKey] ?? 10 * 1024 * 1024;  // default 10MB if unmatched
    const maxSizePerFile = perFileLimits[sizeKey] ?? 10 * 1024 * 1024;

    const isShopVideos = sizeKey.includes("shop videos");
    const isShopPhotos = sizeKey.includes("shop photos");
    const isAadhaar = sizeKey.includes("aadhaar card");
    const isPan = sizeKey.includes("pan card");
    const isElectricityBill = sizeKey.includes("electricity bill");
    const isMoaAoa = sizeKey.includes("moa or aoa");

    let totalSize = 0;
    const dictKey = $fileUpload[0].name;
    if (self.SH_FILE_DATA_DICTIONARY[dictKey]) {
        for (const uploaded of self.SH_FILE_DATA_DICTIONARY[dictKey]) {
            totalSize += atob(uploaded.datas).length;
        }
    }

    for (const file of $fileUpload[0].files) {
        if (isShopVideos && !videoTypes.includes(file.type)) {
            alert(`"${sizeKey}" only accepts video files.`);
            $fileUpload.val('');
            return;
        }
        if (isShopPhotos && !imageTypes.includes(file.type)) {
            alert(`"${sizeKey}" only accepts image files.`);
            $fileUpload.val('');
            return;
        }
        if ((isAadhaar || isPan) && ![...imageTypes, ...pdfTypes].includes(file.type)) {
            alert(`"${sizeKey}" only accepts image or PDF files.`);
            $fileUpload.val('');
            return;
        }
        if (!isShopVideos && !isShopPhotos && !(isAadhaar || isPan)
            && ![...imageTypes, ...pdfTypes, ...officeTypes].includes(file.type)) {
            alert(`Only image, PDF, or Office docs allowed for "${sizeKey}".`);
            $fileUpload.val('');
            return;
        }
        console.log("file.sixe and masxx", file.size, maxSizePerFile)
         if (file.size > maxSizePerFile) {
            alert(`Each file for "${sizeKey}" must be ≤ ${(maxSizePerFile / 1024 / 1024).toFixed(1)} MB.`);
            $fileUpload.val('');
            return;
        }
         if (isShopPhotos || isShopVideos || isElectricityBill || isMoaAoa) {
            let existingCount = self.SH_FILE_DATA_DICTIONARY[dictKey] ? self.SH_FILE_DATA_DICTIONARY[dictKey].length : 0;
            let maxAllowed = maxFilesPerField[sizeKey];
            if (existingCount + $fileUpload[0].files.length > maxAllowed) {
                alert(`"${sizeKey}" allows only ${maxAllowed} file${maxAllowed > 1 ? 's' : ''}.`);
                $fileUpload.val('');
                return;
            }
            totalSize += file.size;
            if (totalSize > maxSizePerField) {
                alert(
                    `Total upload for "${sizeKey}" exceeds ${ (maxSizePerField / 1024 / 1024).toFixed(1) } MB. `
                    + `You selected ${ (totalSize / 1024 / 1024).toFixed(1) } MB.`
                );
                $fileUpload.val('');
                delete self.SH_FILE_DATA_DICTIONARY[dictKey];
                return;
            }
        }
        const result = await toBase64(file);
        const base64data = result.split(',')[1];
        FILE_LIST.push({ fname: file.name, type: file.type, datas: base64data });
    }

    if (!self.SH_FILE_DATA_DICTIONARY[dictKey]) {
        self.SH_FILE_DATA_DICTIONARY[dictKey] = [];
    }
    self.SH_FILE_DATA_DICTIONARY[dictKey].push(...FILE_LIST);
},

        /**
         * If user types in Legal Name and radio "Yes" is selected, update Trade Name
         */
    _onLegalNameChangeInit: function () {
        const $legalNameInput = $('.js_question-wrapper')
            .filter((_, el) => $(el).text().replace(/\s+/g, ' ').trim().includes("Business Legal Name"))
            .find('input.o_survey_question_text_box');

        const $tradeNameInput = $('.js_question-wrapper')
            .filter((_, el) => $(el).text().replace(/\s+/g, ' ').trim().includes("Business Trade Name"))
            .find('input.o_survey_question_text_box');

        const $radioWrapper = $('.js_question-wrapper').filter((_, el) =>
            $(el).text().replace(/\s+/g, ' ').trim().includes("If Trade Name is same as Legal Name")
        );

        const matchPhrases = [
            "Yes",
            "Yes (If Trade Name is same as Legal Name)",
        ];

        const isYesSelected = function () {
            const $selectedYesRadio = $radioWrapper.find('input[type="radio"]:checked');
            const selectedAnswerLabel = $selectedYesRadio.closest('label').text().replace(/\s+/g, ' ').trim();
            return matchPhrases.some((phrase) =>
                selectedAnswerLabel.toLowerCase().includes(phrase.toLowerCase())
            );
        };

        const updateTradeName = function () {
            if (isYesSelected()) {
                $tradeNameInput.val($legalNameInput.val()).prop('readonly', true);
            } else {
                $tradeNameInput.prop('readonly', false);
            }
        };

        // Sync only when "Yes" is selected
        $legalNameInput.on('input', function () {
            if (isYesSelected()) {
                $tradeNameInput.val($legalNameInput.val());
            }
        });

        // Radio button changes
        $radioWrapper.find('input[type="radio"]').on('change', function () {
            if (isYesSelected()) {
                $tradeNameInput.val($legalNameInput.val()).prop('readonly', true);
            } else {
                $tradeNameInput.prop('readonly', false).val('');
            }
        });

        // Init check
        updateTradeName();
    },


    /**
     * Check if the URL is a valid or not.
     * @private
     */
    _validateURL: function (URL) {
        
        var expression = /(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})/gi;
        var regex = new RegExp(expression);
    

            if (URL.match(regex)) {
                return true;
            } else {
                return false;
            }

        },

    // VALIDATION TOOLS
    // -------------------------------------------------------------------------
    /**
    * Validation is done in frontend before submit to avoid latency from the server.
    * If the validation is incorrect, the errors are displayed before submitting and
    * fade in / out of submit is avoided.
    *
    * Each question type gets its own validation process.
    *
    * There is a special use case for the 'required' questions, where we use the constraint
    * error message that comes from the question configuration ('constr_error_msg' field).
    *
    * @private
    */
    _validateForm: function ($form, formData) {
        var self = this;
        var errors = {};
        var validationEmailMsg = _t("This answer must be an email address.");
        var validationDateMsg = _t("This is not a date");

        this._resetErrors();
        const loader = document.getElementById('survey_submit_loader');
        var data = {};
        formData.forEach(function (value, key) {
            data[key] = value;
        });


        var inactiveQuestionIds = this.options.sessionInProgress ? [] : this._getInactiveConditionalQuestionIds();

        $form.find('[data-question-type]').each(function () {
            var $input = $(this);
            var $questionWrapper = $input.closest(".js_question-wrapper");
            var questionId = $questionWrapper.attr('id');

            // If question is inactive, skip validation.
            if (inactiveQuestionIds.includes(parseInt(questionId))) {
                return;
            }

            var questionRequired = $questionWrapper.data('required');
            var constrErrorMsg = $questionWrapper.data('constrErrorMsg');
            var validationErrorMsg = $questionWrapper.data('validationErrorMsg');
            switch ($input.data('questionType')) {
                case 'char_box':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    } else if ($input.val() && $input.attr('type') === 'email' && !self._validateEmail($input.val())) {
                        errors[questionId] = validationEmailMsg;
                    } else {
                        var lengthMin = $input.data('validationLengthMin');
                        var lengthMax = $input.data('validationLengthMax');
                        var length = $input.val().length;
                        if (lengthMin && (lengthMin > length || length > lengthMax)) {
                            errors[questionId] = validationErrorMsg;
                        }
                    }
                    break;
                case 'text_box':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;
                case 'numerical_box':
                    if (questionRequired && !data[questionId]) {
                        errors[questionId] = constrErrorMsg;
                    } else {
                        var floatMin = $input.data('validationFloatMin');
                        var floatMax = $input.data('validationFloatMax');
                        var value = parseFloat($input.val());
                        if (floatMin && (floatMin > value || value > floatMax)) {
                            errors[questionId] = validationErrorMsg;
                        }
                    }
                    break;
                case 'date':
                case 'datetime':
                    if (questionRequired && !data[questionId]) {
                        errors[questionId] = constrErrorMsg;
                    } else if (data[questionId]) {
                        const [parse, deserialize] =
                            $input.data("questionType") === "date"
                                ? [parseDate, deserializeDate]
                                : [parseDateTime, deserializeDateTime];
                        const date = parse($input.val());
                        if (!date || !date.isValid) {
                            errors[questionId] = validationDateMsg;
                        } else {
                            const maxDate = deserialize($input.data('max-date'));
                            const minDate = deserialize($input.data('min-date'));
                            if (
                                (maxDate.isValid && date > maxDate) ||
                                (minDate.isValid && date < minDate)
                            ) {
                                errors[questionId] = validationErrorMsg;
                            }
                        }
                    }
                    break;
                case 'simple_choice_radio':
                case 'multiple_choice':
                    if (questionRequired) {
                        var $textarea = $questionWrapper.find('textarea');
                        if (!data[questionId]) {
                            errors[questionId] = constrErrorMsg;
                        } else if (data[questionId] === '-1' && !$textarea.val()) {
                            // if other has been checked and value is null
                            errors[questionId] = constrErrorMsg;
                        }
                    }
                    break;
                case 'matrix':
                    const MatrixTableFile = $questionWrapper.find('table.o_survey_question_matrix');
                    const matrixSubtype = MatrixTableFile.data('matrix-subtype');
                    const questionCode = MatrixTableFile.data('question-code');
                    if (matrixSubtype === "sh_custom_matrix" && questionCode === 'DIR_DETAILS' && questionRequired &&  MatrixTableFile.find('input[type="file"]').length) {
                        let hasError = false;
                        MatrixTableFile.find('tbody tr:visible').each(function () {
                          const $fileInput = $(this).find('input[type="file"]');
                            if (!$fileInput.val() || $fileInput.val().trim() === "") {
                                console.log("haserror called");
                                hasError = true;
                                return false;
                            }
                        });
                        if (hasError) {
                            errors[questionId] = constrErrorMsg;
                        }
                    }
                    else if (matrixSubtype === "sh_custom_matrix" && questionCode !== 'DIR_DETAILS' && questionRequired  &&  MatrixTableFile.find('input[type="file"]').length) {
                        const $fileInput = MatrixTableFile.find('tbody tr:visible').first().find('input[type="file"]');
                        if (!$fileInput.val() || $fileInput.val().trim() === "") {
                            errors[questionId] = constrErrorMsg;
                        }
                    }
                    else if (matrixSubtype !== "sh_custom_matrix" && questionRequired) {
                        const subQuestionsIds = $questionWrapper.find('table').data('subQuestions');
                        // Highlight unanswered rows' header
                        const questionBodySelector = `div[id="${questionId}"] > .o_survey_question_matrix > tbody`;
                        subQuestionsIds.forEach((subQuestionId) => {
                            if (!(`${questionId}_${subQuestionId}` in data)) {
                                errors[questionId] = constrErrorMsg;
                                self.el.querySelector(`${questionBodySelector} > tr[id="${subQuestionId}"] > th`).classList.add('bg-danger');
                            }
                        });
                    }
                    break;
                case 'que_sh_email':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }
                    if ($input.val() && !self._validateEmail($input.val())) {
                        errors[questionId] = validationEmailMsg;
                    }                        
                    break;
                case 'que_sh_url':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }
                    if ($input.val() && !self._validateURL($input.val())) {
                        errors[questionId] = _t("This answer must be an URL.");
                    }                        
                    break;

                case 'que_sh_time':
                    var validationTimeErrorMsg = $input.parents('.js_question-wrapper').attr('data-validation-error-msg')
                    
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }
                    if($input.val()){
                        var min = $input.attr('min')
                        var max = $input.attr('max')
                        var value = parseFloat($input.val())

                        if(parseFloat(min) > value || parseFloat(max) < value){
                            errors[questionId] = validationTimeErrorMsg || _('Time formate is not define properly.');
                        }

                    }
                    break;       

                case 'que_sh_week':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;


                case 'que_sh_month':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;
                case 'que_sh_password':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;

                case 'que_sh_file':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;

                case 'que_sh_signature':
                    
                    var $pad = $input.closest(".js_cls_sh_signature_wrapper").find(".js_cls_sh_signature_pad");
                    var datapad = $pad.jSignature("getData", "native");
                    if (questionRequired && datapad.length == 0) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;
                case 'que_sh_many2one':
                    const MatrixTableSelect = $questionWrapper.find('table.o_survey_question_matrix');
                    if (questionRequired && MatrixTableSelect.length) {
                        //const $firstSelect = MatrixTableSelect.find('tbody tr:visible').first().find('select');
                        const $firstSelect = MatrixTableSelect.find('tbody tr:visible').first().find('.js_cls_sh_matrix_many2one_select');
                        if (!$firstSelect.val() || $firstSelect.val().trim() === "") {
                            errors[questionId] = constrErrorMsg;
                            //$firstSelect.addClass('is-invalid');
                        } /*else {
                            $firstSelect.removeClass('is-invalid');
                        }*/
                    }
                    else if (!MatrixTableSelect.length && questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;
                case 'que_sh_many2many':
                    if (questionRequired && $input.find('.selected-items span').length == 0) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;
                case 'que_sh_address':
                    if (questionRequired && !$input.val() && !$input.hasClass('js_cls_state_id')) {
                        errors[questionId] = constrErrorMsg;
                    }
                    break;
            }
        });
   // Validate fields with conditional required
   let isValid = true;
   let errorMap = {};
   if (self.validatedEmails) {
        $form.find('input[data-question-code="vendor_email"]').each(function () {
            const $input = $(this);
            const qId = $input.closest(".js_question-wrapper").attr("id");
            if (self.validatedEmails[qId] === false) {
                errorMap[qId] = self.VENDOR_EMAIL_NOT_FOUND;
            }
        });
    }
   $form.find('[data-cond-required="1"]').each(function () {
        const $input = $(this);
        const questionId = $input.attr('name');
        if (!$input.val() || $input.val().trim() === '') {
            //$input.addClass('is-invalid');
            //isValid = false;
            errorMap[questionId] = "This question requires an answer.";
        } else {
            //$input.removeClass('is-invalid');
        }
    });

    let combinedErrors = { ...errors, ...errorMap };

    // Sort by questionId ascending
    combinedErrors = Object.keys(combinedErrors)
        .sort((a, b) => parseInt(a) - parseInt(b))
        .reduce((acc, key) => {
            acc[key] = combinedErrors[key];
            return acc;
    }, {});

    // Single check for any errors
    if (Object.keys(combinedErrors).length > 0) {
        //console.log("combinedErrors", combinedErrors)
        this._showErrors(combinedErrors);
        if (loader) loader.classList.add('d-none'); // hide loader
        return false;
    }
    // End
    /*if (Object.keys(errors).length > 0) {
        console.log("errors>>>>>>>>>>>>>>>>>", errors);
        this._showErrors(errors);
        return false;
    }*/
    if (loader) loader.classList.remove('d-none'); // show loader
    return true;
    },

    
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * GET COUNTRIES
     * @private
     */
    getCountries: function () {
        var self = this;
        var $countrySelects = self.$target.find(".js_cls_country_id");
        
        if ($countrySelects.length) {
            rpc("/survey/get_countries").then(function (data) {
                jQuery.each(data.countries, function (key, value) {
                    var opt = $("<option>").text(value.name).attr("value", value.id);
                    $countrySelects.append(opt);
                });
            });
        }
    },

    /**
     * GET Many2one Field Data
     * @private
     */
    getMany2oneFieldData: async function () {
        var self = this;
        var $m2oSelects = self.$target.find(".js_cls_sh_many2one_select");
        if ($m2oSelects.length) {
            await $m2oSelects.each(function (index, element) {
            var ansValue = $(this).attr("value") || false;
                var model_id = $(this).attr("data-model_id") || false;
                if (model_id) {
                    rpc("/survey/get_many2one_field_data", {
                        'model_id': parseInt(model_id),
                    }).then(function (data) {
                        jQuery.each(data.records, function (key, value) {
                            var opt = $("<option>").text(value.name).attr("value", value.name);
                            if (value.name === ansValue) {
                                opt.attr("selected", "selected");
                            }
                            $(element).append(opt);
                        });
                    });
                }
            });
        }
    },

    /**
     * GET Many2many Field Data
     * @private
     */
    getMany2manyFieldData: function () {
        var self = this;
        var $m2oSelects = self.$target.find(".js_cls_sh_many2many_select");
        if ($m2oSelects.length) {
            $m2oSelects.each(function (index, element) {
                var model_id = $(this).attr("data-model_id") || false;
                if (model_id) {
                    rpc("/survey/get_many2many_field_data", {
                        'model_id': parseInt(model_id),
                    }).then(function (data) {
                        jQuery.each(data.records, function (key, value) {
                            var opt = $("<option>").text(value.name).attr("value", value.name);
                            $(element).append(opt);
                        });

                        //init multi select
                        $(element).filterMultiSelect();
                    });
                }
            });
        }
    },

    /**
     * GET Signature Field Data
     * @private
     */
    getSignatureFieldData: function () {
        var self = this;
        var $SignPad = self.$target.find(".js_cls_sh_signature_pad");
        if ($SignPad.length) {
            $SignPad.jSignature({
                "background-color": "#808080",
                'width': 1102,
                'height': 276
            });
        }
    },

    /**
     * Will automatically focus on the first input to allow the user to complete directly the survey,
     * without having to manually get the focus (only if the input has the right type - can write something inside -)
     */
    _focusOnFirstInput: function () {
        this._super.apply(this, arguments);

        if (this.$(".js_cls_country_id").length) {
            this.getCountries();
        }

        if (this.$(".js_cls_sh_many2one_select").length) {
            this.getMany2oneFieldData();
        }

        if (this.$(".js_cls_sh_many2many_select").length) {
            this.getMany2manyFieldData();
        }

        if (this.$(".js_cls_sh_signature_wrapper").length) {
            this.getSignatureFieldData();
        }
    },

    _onClickSignatureClearButton: function (ev) {
        var $clearButton = $(ev.currentTarget);
        var self = this;
        var $signpad = $clearButton.closest(".js_cls_sh_signature_wrapper").find(".js_cls_sh_signature_pad");
        $signpad.jSignature("reset");
    },

    /**
     *   _onChangeCountry .
     */

    _onChangeCountry: function (ev) {
        var $countrySelect = $(ev.currentTarget);
        var self = this;
        if (!$(ev.currentTarget).val()) {
            return;
        }
        var url = "/survey/get_ountry_info/" + $(ev.currentTarget).val()
        rpc(url).then(function (data) {
            // populate states and display
            var $stateSelect = $countrySelect.closest(".js_cls_sh_address_wrapper").find(".js_cls_state_id");
            // dont reload state at first loading (done in qweb)
            if ($stateSelect.length) {
                if ($stateSelect.data("init") === 0 || $stateSelect.find("option").length === 1) {
                    if (data.states.length || data.state_required) {
                        $stateSelect.html("");
                        jQuery.each(data.states, function (key, value) {
                            var opt = $("<option>").text(value[1]).attr("value", value[0]).attr("data-code", value[2]);
                            $stateSelect.append(opt);
                        });
                        $stateSelect.parent("div").show();
                    } else {
                        $stateSelect.val("").parent("div").hide();
                    }
                    $stateSelect.data("init", 0);
                } else {
                    $stateSelect.data("init", 0);
                }
            }
        });
    },

    /**
     *   Prepare Address answers before submitting form.
     */
    _prepareSubmitAnswersAddress: function (params, questionId, $address_ele) {
        var self = this;
        var $addressWrapper = $address_ele.closest(".js_cls_sh_address_wrapper");
        var street = $addressWrapper.find(".js_cls_street").val() || "";
        var street2 = $addressWrapper.find(".js_cls_street2").val() || "";
        var city = $addressWrapper.find(".js_cls_city").val() || "";
        var zip = $addressWrapper.find(".js_cls_zip").val() || "";
        var country_id = $addressWrapper.find(".js_cls_country_id").val() || "";
        var state_id = $addressWrapper.find(".js_cls_state_id").val() || "";

        if (street || street2 || city || zip || country_id || state_id) {
            var complete_address = "&street=" + street + "&street2=" + street2 + "&city=" + city + "&zip=" + zip + "&country_id=" + country_id + "&state_id=" + state_id;
            params[questionId] = complete_address;
        }
        return params;
    },

    /**
     *   Prepare Many2many answers before submitting form.
     */
    _prepareSubmitAnswersMany2many: function (params, $many2many_select_ele, questionId) {
        var self = this;
        $many2many_select_ele.find("input:checked").each(function () {
            if ($(this).val() != "") {
                params = self._prepareSubmitAnswer(params, questionId, $(this).val());
            }
        });
        params = self._prepareSubmitComment(params, $many2many_select_ele, questionId, false);
        return params;
    },

    /**
     *   Prepare Signature answers before submitting form.
     */
    _prepareSubmitAnswersSignature: function (params, questionId, $signature_input_ele) {
        var self = this;
        var pad = $signature_input_ele.closest(".js_cls_sh_signature_wrapper").find(".js_cls_sh_signature_pad");
        var datapair = pad.jSignature("getData", "image");
        params[questionId] = datapair[1];
        return params;
    },

    _prepareSubmitValues: function (formData, params) {
    var self = this;
    formData.forEach(function (value, key) {
        switch (key) {
            case "csrf_token":
            case "token":
            case "page_id":
            case "question_id":
                params[key] = value;
                break;
        }
    });

    // Get all question answers by question type
    let submissionPrevented = false;  // ✅ Declare at the top
    this.$("[data-question-type]").each(function () {
        if (submissionPrevented) return false;  // ✅ Stop if invalid selection was found

        switch ($(this).data("questionType")) {
            case 'text_box':
            case 'char_box':
            case 'numerical_box':
                params[this.name] = this.value;
                break;
            case 'date':
            case 'datetime': {
                const [parse, serialize] =
                    $(this).data("questionType") === "date"
                        ? [parseDate, serializeDate]
                        : [parseDateTime, serializeDateTime];
                const date = parse(this.value);
                params[this.name] = date ? serialize(date) : "";
                break;
            }
            case 'simple_choice_radio':
            case 'multiple_choice':
                params = self._prepareSubmitChoices(params, $(this), $(this).data('name'));
                break;
            case 'matrix':
                params = self._prepareSubmitAnswersMatrix(params, $(this));
                break;
            case "que_sh_color":
            case "que_sh_email":
            case "que_sh_url":
            case "que_sh_time":
            case "que_sh_range":
            case "que_sh_week":
            case "que_sh_month":
            case "que_sh_password":
                params[this.name] = this.value;
                break;
            case "que_sh_file":
                params[this.name] = self.SH_FILE_DATA_DICTIONARY[this.name] || []
                break;
            case "que_sh_address":
                params = self._prepareSubmitAnswersAddress(params, this.name, $(this));
                break;

            case "que_sh_many2one":
                    params[this.name] = $(this).parent().find("input").val();
                    break;

            // ✅ Fixed many2one logic
//            case "que_sh_many2one": {
//                const $input = $(this).parent().find("input");
//                const userInput = $input.val()?.trim();
//                const datalistId = $input.attr("list");
//                const $datalist = $("#" + datalistId);
//
//                const validOptions = $datalist.find("option").map(function () {
//                    return $(this).val();
//                }).get();
//
//                const selectedVal = validOptions.includes(userInput) ? userInput : "";
//
//                if (selectedVal) {
//                    params[this.name] = selectedVal;
//                } else {
//                    const label = $(this)
//                        .closest(".js_question-wrapper")
//                        .find(".o_survey_question_title, h3 span")
//                        .text()
//                        .trim();
//
//                    alert(`Please select a valid option for "${label}" from the dropdown list.`);
//                    submissionPrevented = true;
//                    return false; // 🚫 Stop further processing
//                }
//                break;
//            }

            case "que_sh_many2many":
                params = self._prepareSubmitAnswersMany2many(params, $(this), $(this).attr("name"));
                break;
            case "que_sh_signature":
                params = self._prepareSubmitAnswersSignature(params, this.name, $(this));
                break;
        }
    });
},
});

