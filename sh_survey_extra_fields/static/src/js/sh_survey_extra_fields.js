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
        "input input[type='range'].o_survey_question_email_box": "_onInputRangeValueChange",            
    }),

    /**
     * @override
     */
    init: function () {
        this.SH_FILE_DATA_DICTIONARY = {};
        this._super.apply(this, arguments);
    },
    
    _onInputRangeValueChange: function (ev) {
        var $input = $(ev.currentTarget);
        $input.next('label').html($input.val())
    },
    
    /**
     * @private
     * @param {FileInputEvent} ev
     */
    _onChangeFileInput: async function (ev) {
    var self = this;
    var $fileUpload = $(ev.currentTarget);

    if (!$fileUpload.length) return;

    // 🔒 File type groups
    const imageTypes = [
        'image/jpeg', 'image/png', 'image/jpg', 'image/gif',
        'image/bmp', 'image/webp', 'image/svg+xml'
    ];

    const videoTypes = [
        'video/mp4', 'video/mpeg', 'video/ogg',
        'video/webm', 'video/avi', 'video/quicktime'
    ];

    const pdfTypes = ['application/pdf'];

    const officeTypes = [
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  // docx
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',        // xlsx
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation' // pptx
    ];

    const FILE_LIST = [];

    const toBase64 = (file) => new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
        reader.readAsDataURL(file);
    });

    // 🔍 Get the question label (e.g., "Shop Photos", "Shop Videos")
    const labelText = $fileUpload
        .closest('.js_question-wrapper')
        .find('.o_survey_question_title, h3 span')
        .first()
        .text()
        .trim()
        .toLowerCase();

    const isShopVideos = labelText.includes("shop videos");
    const isShopPhotos = labelText.includes("shop photos");

    for (let i = 0; i < $fileUpload[0].files.length; i++) {
        const file = $fileUpload[0].files[i];

        // 🔒 "Shop Videos" → only videos
        if (isShopVideos && !videoTypes.includes(file.type)) {
            alert(`Invalid file type for "${labelText}". Only video files are allowed.`);
            $fileUpload.val('');
            return;
        }

        // 🔒 "Shop Photos" → only images
        if (isShopPhotos && !imageTypes.includes(file.type)) {
            alert(`Invalid file type for "${labelText}". Only image files are allowed.`);
            $fileUpload.val('');
            return;
        }

        // 🔒 Others → allow image + PDF + Office
        if (
            !isShopVideos &&
            !isShopPhotos &&
            ![...imageTypes, ...pdfTypes, ...officeTypes].includes(file.type)
        ) {
            alert(`Invalid file type: ${file.name}\n\nOnly image, PDF, or Office documents are allowed.`);
            $fileUpload.val('');
            return;
        }

        // ✅ Convert to base64 and store
        const result = await toBase64(file);
        const base64data = result.split(',')[1];
        if (base64data) {
            FILE_LIST.push({
                'fname': file.name,
                'type': file.type,
                'datas': base64data
            });
        }
    }

    // ✅ Assign to dictionary
    self.SH_FILE_DATA_DICTIONARY[$fileUpload[0].name] = FILE_LIST;
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
                    if (questionRequired) {
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
                    if (questionRequired && !$input.val()) {
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
        if (Object.keys(errors).length > 0) {
            this._showErrors(errors);
            return false;
        }
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
        this.$("[data-question-type]").each(function () {
            switch ($(this).data("questionType")) {
                case 'text_box':
                case 'char_box':
                case 'numerical_box':
                    params[this.name] = this.value;
                    break;
                case 'date':
                case 'datetime':{
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
                    params[this.name] = this.value;
                    break;
                case "que_sh_email":
                    params[this.name] = this.value;
                    break;
                case "que_sh_url":
                    params[this.name] = this.value;
                    break;
                case "que_sh_time":
                    params[this.name] = this.value;
                    break;
                case "que_sh_range":
                    params[this.name] = this.value;
                    break;
                case "que_sh_week":
                    params[this.name] = this.value;
                    break;
                case "que_sh_month":
                    params[this.name] = this.value;
                    break;
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

