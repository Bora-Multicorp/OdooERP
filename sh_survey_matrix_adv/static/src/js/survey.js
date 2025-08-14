/** @odoo-module **/

import SurveyFormWidget from '@survey/js/survey_form';
import { rpc } from "@web/core/network/rpc";


/*function reloadMany2oneOptions({ model_id, domain, $el, selectedId = null }) {
    rpc("/survey/get_matrix_many2one_field_data", {
        model_id: model_id,
        domain: domain,
    }).then(function (data) {
        $el.empty();
        $el.append($('<option>').text('Select...').val(''));
        $.each(data.records, function (index, record) {
            const opt = $("<option>").text(record.name).attr("value", record.id);
            if (selectedId && selectedId === record.id) {
                opt.attr("selected", "selected");
            }
            $el.append(opt);
        });
    });
}


$(document).on("change", ".js_cls_sh_matrix_many2one_select", function (ev) {
    const $el = $(this);
    const rowId = $el.data('row-id');
    const modelName = $el.data('model-name');
    const selectedValue = $el.val();
    if (modelName === 'res.country') {
        const $stateField = $(`select[data-model-name='res.country.state'][data-row-id='${rowId}']`);
        if ($stateField.length && selectedValue) {
            reloadMany2oneOptions({
                model_id: $stateField.data('model_id'),
                domain: [['country_id', '=', parseInt(selectedValue)]],
                $el: $stateField,
            });
        }
    }
 if (modelName === 'res.country.state') {
    if (selectedValue) {
        const stateId = parseInt(selectedValue);  // save current state
        rpc("/web/dataset/call_kw", {
            model: 'res.country.state',
            method: 'read',
            args: [[stateId], ['country_id']],
            kwargs: {},
        }).then(function (result) {
            if (result.length && result[0].country_id) {
                const countryId = result[0].country_id[0];
                const $countryField = $(`select[data-model-name='res.country'][data-row-id='${rowId}']`);
                const $stateField = $(`select[data-model-name='res.country.state'][data-row-id='${rowId}']`);
                if ($countryField.length && $stateField.length) {
                    $countryField.val(countryId); // set country
                    reloadMany2oneOptions({
                        model_id: $stateField.data('model_id'),
                        domain: [['country_id', '=', countryId]],
                        $el: $stateField,
                        selectedId: stateId, // reset selected state after reload
                    });
                }
            }
        });
    }
}
});*/


$(document).on("change", ".sh_file_input", function (ev) {
    var $i = $(ev.currentTarget);
    var input = $i[0];
    var file_data = "";
    if (input.files && input.files[0]) {
        var file = input.files[0]; // The file
        var fr = new FileReader(); // FileReader instance
        fr.onload = function () {
            file_data = fr.result;
            if (file_data) {
                //$(ev.currentTarget).parent().find(".sh_file_input_data").val(file_data.split(",")[1]);
                const base64Content = file_data.split(",")[1];
                const fileName = file.name;
                const $textInput = $i.parent().find(".sh_file_input_data");
                $textInput.val(base64Content);
                $textInput.attr("data-filename", fileName);
            }
        };
        fr.readAsDataURL(file);
    }
});

function normalize(str) {
    return str.replace(/\s+/g, ' ').trim();
}

function updateRowCount(data_name) {
    const visibleRows = $('table.table-borderless[data-name="' + data_name + '"] tr[id]').not('.hide-row');
    const rowCount = visibleRows.length;
    $('input[name="' + data_name + '_rowcount"]').val(rowCount);
}

$(document).off('click', '.add-item-btn').on('click', '.add-item-btn', function(ev) {
    //var find_row = $('table.table-borderless').find('tr.hide-row:first');
    var data_name = $(ev.currentTarget).attr('data-name')
    var find_row = $('table.table-borderless[data-name=' + data_name +']').find('tr.hide-row:first');
    //var rowCount = $('#myTable tr').length;
    if (! find_row.length){
       alert('Maximum Limit reached to add records');
    }
    find_row.removeClass('hide-row');
    updateRowCount(data_name);
});

$(document).off('click', '.delete-item-btn').on('click', '.delete-item-btn', function(ev) {
    var find_row = $(ev.target).closest('tr');
    $(ev.target).closest('tr').addClass('hide-row');
    updateRowCount(data_name);
});

//function waitForMatrixTableAndHide() {
//    const $visibleMatrix = $("table.o_survey_question_matrix:visible");
//    if ($visibleMatrix.length > 0) {
//        $visibleMatrix.each(function () {
//            const $rows = $(this).find("tbody > tr");
//            if ($rows.length > 1) {
//                $rows.addClass("hide-row");
//                $rows.first().removeClass("hide-row");
//            }
//        });
//    } else {
//        // Retry again after delay, DOM probably not ready yet
//        setTimeout(waitForMatrixTableAndHide, 50);
//    }
//}



//function showDirectorDetailsMatrix(maxCount) {
//    if (!Number.isInteger(maxCount) || maxCount <= 0) {
//        return;
//    }
//    const $headingSpan = $("span.text-break").filter(function () {
//        return $(this).text().trim().includes("Director Details");
//    });
//    if (!$headingSpan.length) {
//        return;
//    }
//    const $headingDiv = $headingSpan.closest("div.mb-4");
//    const $matrixTable = $headingDiv.nextAll("table[data-question-type='matrix']").first();
//    if (!$matrixTable.length) {
//        return;
//    }
//    const $rows = $matrixTable.find("tr");
//    $rows.addClass("hide-row");
//    $rows.slice(0, maxCount + 1).removeClass("hide-row");
//}

// Triggered on survey page navigation
//$(document).on("click", "button[type='submit'][value='next'], #next_page", function () {
//    setTimeout(waitForMatrixTableAndHide, 100);
//    setTimeout(function () {
//        const directorCount = parseInt(sessionStorage.getItem("director_details_count") || "0");
//        showDirectorDetailsMatrix(directorCount);
//    }, 500); // Adjust delay if needed
//});

SurveyFormWidget.include({
   events: Object.assign({}, SurveyFormWidget.prototype.events || {}, {
        'change input[type="radio"]': '_onChangeSelection',
        //'change .js_cls_sh_matrix_many2one_select': '_onChangeState',
        'input .js_cls_sh_matrix_many2one_select': '_onInputState',
    }),

    init: function () {
        this._super.apply(this, arguments);
        this._selectedConstBusValue = null;
    },

    _onInputState: function (ev) {
        var $input = $(ev.currentTarget);
        var modelName = $input.data('model-name');
        var rowId = $input.data('row-id');

        if (modelName === 'res.country.state') {
            // Find the country input for the same row
            const $countryField = $(`input[data-model-name='res.country'][data-row-id='${rowId}']`);
            console.log("$countryField", $countryField);

            if ($countryField.length && !$countryField.val()) {
                const $datalist = $("#" + $countryField.attr('list'));
                const $indiaOption = $datalist.find("option[value='India']");
                if ($indiaOption.length) {
                    $countryField.val('India');
                    console.log("India auto-selected");
                }
            }
        }
    },



    /*_onChangeState: function (ev) {
        var $StateSelect = $(ev.currentTarget);
        var self = this;
        if (!$StateSelect.val() || !$StateSelect.find('option:selected').length) {
            return;
        }
        const rowId = $StateSelect.data('row-id');
        const modelName = $StateSelect.data('model-name');
        if (modelName === 'res.country.state') {
            const $countryField = $(`select[data-model-name='res.country'][data-row-id='${rowId}']`);
            var indiaId = $countryField.find("option:contains('India')").val();
            if ($countryField.length) {
                $countryField.val(indiaId).trigger('change');
            }
        }
    },*/

    applyConditionalRequirements: function ($input) {
        if (!$input || !$input.length) {
            return;
        }
        const selectedAnswerId = parseInt($input.val());
        if (!selectedAnswerId) return;
        // Reset all conditional fields
        $('[data-cond-required="1"]').each(function () {
            $(this).removeAttr('data-required data-cond-required').removeClass('is-invalid');
            const fieldCode = $(this).data('question-code');
            $('[data-cond-required-label="' + fieldCode + '"]').addClass("d-none");
        });
        // Re-apply conditions based on selected answer
        $('input[data-cond-req-questions]').each(function () {
            const $targetInput = $(this);
            const condReqIds = $targetInput.data('cond-req-questions');
            if (Array.isArray(condReqIds) && condReqIds.includes(selectedAnswerId)) {
                $targetInput.attr({
                    'data-required': 'true',
                    'data-cond-required': '1'
                });
                const targetCode = $targetInput.data('question-code');
                $('[data-cond-required-label="' + targetCode + '"]').removeClass("d-none");
            }
        });
    },

    updateDirectorMatrixRowVisibility: function (count) {
        $("div.mb-4").each(function () {
            const headingText = $(this).text().trim();
            if (headingText.startsWith("Director Details")) {
                const $matrixTable = $(this).nextAll("table[data-question-type='matrix']").first();
                if (!$matrixTable.length) return;
                const dataName = $matrixTable.attr("data-name");
                const inputSelector = `input[name="${dataName}_rowcount"]`;
                const $rowCountInput = $(inputSelector);
                if ($rowCountInput.length) {
                    $rowCountInput.val(count).trigger("change");
                    const $rows = $matrixTable.find("tbody > tr");
                    $rows.each(function (index) {
                        if (index < count) {
                            $(this).removeClass("hide-row");
                        } else {
                            $(this).addClass("hide-row");
                        }
                    });
                }
            }
        });
    },


    _onChangeSelection: function (event) {
        const $input = $(event.target);
        if (!$input.val()) {
            return;
        }
        const $questionDiv = $input.closest('.o_survey_answer_wrapper');
        const questionCode = $questionDiv.data('question-code');
        if (questionCode === 'CONST_OF_BUSINESS') {
            this._selectedConstBusValue = $input.val();
            this.applyConditionalRequirements($input);
            const selectedLabel = $input.closest("label").find("span").text().trim();
            const normalizedLabel = normalize(selectedLabel);
            const multiDirectorLabels = [
                "Partnership",
                "Pvt Ltd Co.",
                "LLP",
                "If other, please specify:"
            ].map(normalize);
            let directorCount = 0;
            if (normalizedLabel === "Sole Proprietor" || normalizedLabel === "HUF(Karta)") {
                directorCount = 1;
            } else if (multiDirectorLabels.includes(normalizedLabel)) {
                directorCount = 7;
            }
            if (directorCount > 0) {
                sessionStorage.setItem("director_details_count", directorCount);
                this.updateDirectorMatrixRowVisibility(directorCount);
            }
        }
        if (questionCode === 'NO_OF_MANAGEING_PARTNER') {
            const selectedLabel2 = $input.closest("label").find("span").text().trim()
            const maxCount = parseInt(selectedLabel2);
            if ((isNaN(maxCount) || maxCount <= 0 || maxCount > 7)) {
                sessionStorage.setItem("director_details_count", directorCount);
                this.updateDirectorMatrixRowVisibility(directorCount);
            }
            else if (!isNaN(maxCount) && maxCount > 0 && maxCount <= 7) {
                sessionStorage.setItem("director_details_count", maxCount);
                this.updateDirectorMatrixRowVisibility(maxCount);
            }
        }
    },

    _onNextScreenDone: function (options) {
        const def = this._super.apply(this, arguments);
        if (this._selectedConstBusValue) {
            const $mockInput = $('<input>')
                .attr('type', 'radio')
                .addClass('o_survey_form_choice_item')
                .val(this._selectedConstBusValue);
            this.applyConditionalRequirements($mockInput);
        }
        const storedDirectorCount = sessionStorage.getItem("director_details_count");
        if (storedDirectorCount) {
            this.updateDirectorMatrixRowVisibility(storedDirectorCount);
            sessionStorage.removeItem("director_details_count");
        }
        this.restoreVisibleRows();
        return def;
    },


    restoreVisibleRows: async function () {
        $("table.o_survey_question_matrix").each(function () {
            const $table = $(this);
            const dataName = $table.attr("data-name");
            const rowCountInput = $('input[name="' + dataName + '_rowcount"]');
            const rowCount = parseInt(rowCountInput.val()) || 1;
            const $rows = $table.find("tbody > tr");
            $rows.each(function (index) {
                if (index < rowCount) {
                    $(this).removeClass("hide-row");
                } else {
                    $(this).addClass("hide-row");
                }
            });
          });
    },

  /*  getMatrixMany2oneFieldData: async function () {
        var self = this;
        var $m2oSelects = self.$target.find(".js_cls_sh_matrix_many2one_select");
        if ($m2oSelects.length) {
            await $m2oSelects.each(function (index, element) {
            var ansValue = $(this).attr("value") || false;
            var model_id = $(this).attr("data-model_id") || false;
            if (model_id) {
                rpc("/survey/get_matrix_many2one_field_data", {
                    'model_id': parseInt(model_id),
                }).then(function (data) {
                    jQuery.each(data.records, function (key, value) {
                        //var opt = $("<option>").text(value.name).attr("value", value.name);
                        var opt = $("<option>").text(value.name).attr("value", value.id);
                        //if (value.name === ansValue) {
                        if (String(value.id) === String(ansValue)) {
                            opt.attr("selected", "selected");
                        }
                        $(element).append(opt);
                    });
                });
            }
         });
        }
    },*/

    getMatrixMany2oneFieldData: function () {
        var self = this;
        var $m2oSelects = self.$target.find(".js_cls_sh_matrix_many2one_select");
        if ($m2oSelects.length) {
            $m2oSelects.each(function () {
                var $input = $(this);
                var ansValue = $input.val() || '';  // previous selected name
                var model_id = $input.data("model_id");
                var model_name = $input.data("model-name");
                var domain = [];
                // Only Indian states for res.country.state
                if (model_name === "res.country.state") {
                    domain = [['country_id.code', '=', 'IN']];
                }
                if (model_id) {
                    rpc("/survey/get_matrix_many2one_field_data", {
                        model_id: parseInt(model_id),
                        domain: domain,
                    }).then(function (data) {
                        var $datalist = $("#" + $input.attr('list'));
                        $datalist.empty();
                        $datalist.append($('<option>', { value: '' })); // placeholder
                        data.records.forEach(function (record) {
                            var $opt = $("<option>")
                                .attr("value", record.name)    // show name in input
                                .attr("data-id", record.id);  // store id internally
                            $datalist.append($opt);
                            // Set input value only if previous answer exists
                            if (record.name === ansValue) {
                                $input.val(record.name);
                            }
                        });
                    });
                }
            });
        }
    },


    _prepareSubmitAnswersMatrix: function (params, $matrixTable) {
        var self = this;
        const questionId = $matrixTable.data('name');

        $(".sh_row_count_answer").each(function () {
            const rowCountValue = $(this).val();
            const questionId = $(this).data("question-id");
            if (rowCountValue) {
                params = self._prepareSubmitAnswerMatrixCustom(params, questionId, "rowcount", "rowcount", rowCountValue);
            }
        });

        $matrixTable.find("input").each(function () {
            if (this.type != "file") {
                if ($(this).data("col-id") == this.value && $(this).prop("checked") == true) {
                    params = self._prepareSubmitAnswerMatrix(params, $matrixTable.data("name"), $(this).data("rowId"), this.value);
                } else if ($(this).data("col-id") != this.value) {
                    params = self._prepareSubmitAnswerMatrixCustom(params, $matrixTable.data("name"), $(this).data("rowId"), $(this).data("col-id"), this.value);
                }
            }
        });

        $matrixTable.find(".sh_textarea").each(function () {
            if (this.type != "file") {
                if ($(this).data("col-id") == this.value && $(this).prop("checked") == true) {
                    params = self._prepareSubmitAnswerMatrix(params, $matrixTable.data("name"), $(this).data("rowId"), this.value);
                } else if ($(this).data("col-id") != this.value) {
                    params = self._prepareSubmitAnswerMatrixCustom(params, $matrixTable.data("name"), $(this).data("rowId"), $(this).data("col-id"), this.value);
                }
            }
        });

        $matrixTable.find(".sh_file_input_data").each(function () {
            const rowId = $(this).data("row-id");
            const colId = $(this).data("col-id");
            const base64Content = this.value;
            const fileName = $(this).data("filename") || "";
            if (!base64Content) {
                return;
            }
            const jsonData = JSON.stringify({
                value: base64Content,
                filename: fileName,
            });
            params = self._prepareSubmitAnswerMatrixCustom(params, questionId, rowId, colId, jsonData);
        });

        $matrixTable.find(".sh_m2o").each(function () {
            if (this.type != "file") {
                if ($(this).data("col-id") == this.value && $(this).prop("checked") == true) {
                    params = self._prepareSubmitAnswerMatrix(params, $matrixTable.data("name"), $(this).data("rowId"), this.value);
                } else if ($(this).data("col-id") != this.value) {
                    params = self._prepareSubmitAnswerMatrixCustom(params, $matrixTable.data("name"), $(this).data("rowId"), $(this).data("col-id"), this.value);
                }
            }
        });

        // IN ORDER TO FIX ONE COMMENT SUBMITED WITH TEXTAREAD INPUT
        // IN HTML INSPECT VIEW FOUND THAT MULTIPLE TEXTAREA FIELD RENDERED WHEN CLICK ON
        // TEXTAREA FIELD IN CUSTOM MATRIX SO BELOW IS A LITTLE HACK TO FIX IT.
        if ($matrixTable.find(".sh_textarea").length) {
            return params;
        }

        params = self._prepareSubmitComment(params, $matrixTable.closest(".js_question-wrapper"), $matrixTable.data("name"), true);
        return params;
    },

    _prepareSubmitAnswerMatrix: function (params, questionId, rowId, colId, isComment) {
        var value = questionId in params ? params[questionId] : {};
        if (isComment) {
            value["comment"] = colId;
        } else {
            if (rowId in value) {
                value[rowId].push(colId);
            } else {
                value[rowId] = [colId];
            }
        }
        params[questionId] = value;
        return params;
    },

    _prepareSubmitAnswerMatrixCustom: function (params, questionId, rowId, colId, data, isComment) {
        var value = questionId in params ? params[questionId] : {};
        if (isComment) {
            value["comment"] = colId;
        } else if (colId != data) {
            if (rowId in value) {
                value[rowId + "_" + colId].push(data);
            } else {
                value[rowId + "_" + colId] = [data];
            }
        } else {
            if (rowId in value) {
                value[rowId].push(data);
            } else {
                value[rowId] = [data];
            }
        }
        params[questionId] = value;
        return params;
    },

    /**
     * Will automatically focus on the first input to allow the user to complete directly the survey,
     * without having to manually get the focus (only if the input has the right type - can write something inside -)
     */
    _focusOnFirstInput: function () {
        this._super.apply(this, arguments);

        if (this.$("input[type='range']").length) {
            this.$("input[type='range']").trigger('input')
        }

        if (this.$(".js_cls_sh_matrix_many2one_select").length) {
            this.getMatrixMany2oneFieldData();
        }
    },


});
