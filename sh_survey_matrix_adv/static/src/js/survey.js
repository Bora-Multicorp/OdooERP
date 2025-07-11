/** @odoo-module **/

import SurveyFormWidget from '@survey/js/survey_form';

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
                $(ev.currentTarget).parent().find(".sh_file_input_data").val(file_data.split(",")[1]);
            }
        };
        fr.readAsDataURL(file);
    }
});

SurveyFormWidget.include({
    _prepareSubmitAnswersMatrix: function (params, $matrixTable) {
        var self = this;
        const questionId = $matrixTable.data('name');

        $matrixTable.find('input:text').each(function () {
            params = self._prepareSubmitAnswerMatrixCustom(params, $matrixTable.data('name'), $(this).data('rowId'), $(this).data("col-id"), this.value);
        });

        $matrixTable.find('.sh_textarea').each(function () {
            params = self._prepareSubmitAnswerMatrixCustom(params, $matrixTable.data('name'), $(this).data('rowId'), $(this).data("col-id"), this.value);
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

    _prepareSubmitAnswerMatrixCustom: function (params, questionId, rowId, colId, data, isComment) {
        var value = questionId in params ? params[questionId] : {};
        if (isComment) {
            value['comment'] = colId;
        }
        else if (colId != data) {
            if (rowId in value) {
                value[rowId + "_" + colId].push(data);
            } else {
                value[rowId + "_" + colId] = [data];
            }
        }
        else {
            if (rowId in value) {
                value[rowId].push(colId);
            } else {
                value[rowId] = [colId];
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
    },


});