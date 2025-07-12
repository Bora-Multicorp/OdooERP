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

$(document).on("change", "input.o_survey_form_choice_item", function (event) {
    const $input = $(event.target);
    const selectedOptionId = $input.val();  // This is like 84 (answer_id)
    const selectedLabel = $input.closest("label").find("span").text().trim();  // This gives 1, 2, etc.
    const maxCount = parseInt(selectedLabel || 0);
    //const matrixQuestionId = "206";  // The `data-name` of your <table>
    //const $matrixTable = $(`table.table-borderless[data-name='${matrixQuestionId}']`);
    // Step 1: Find the header <div> that contains the Director Details heading
    const $headingDiv = $("div.mb-4:contains('Director Details')").filter(function () {
        return $(this).text().trim().startsWith("Director Details");
    });
    // Step 2: Get the matrix table that comes after the heading
    const $matrixTable = $headingDiv.nextAll("table[data-question-type='matrix']").first();
    if (!$matrixTable.length) {
        console.warn('Matrix table not found!');
        return;
    }
    const $rows = $matrixTable.find("tr");
    $rows.addClass("hide-row");
    $rows.slice(0, maxCount+1).removeClass("hide-row");
});

//let matrixHidden = false;
//
//function hideInitialMatrixRows() {
//    if (matrixHidden) return;  // Ensure it runs only once
//
//    $("table.o_survey_question_matrix").each(function () {
//        const $rows = $(this).find("tbody > tr");
//        if ($rows.length > 1) {
//            $rows.addClass("hide-row");
//            $rows.first().removeClass("hide-row");
//        }
//    });
//
//    matrixHidden = true;  // Mark it so it won't run again
//}
//
//// Wait for DOM load
//setTimeout(() => {
//    hideInitialMatrixRows();
//}, 1000);  // Adjust timeout based on rendering delay


$(document).off('click', '.add-item-btn').on('click', '.add-item-btn', function(ev) {
    //var find_row = $('table.table-borderless').find('tr.hide-row:first');
    var data_name = $(ev.currentTarget).attr('data-name')
    var find_row = $('table.table-borderless[data-name=' + data_name +']').find('tr.hide-row:first');
    //var rowCount = $('#myTable tr').length;
    if (! find_row.length){
       alert('Maximum Limit reached to add records');
    }
    find_row.removeClass('hide-row');
});

$(document).off('click', '.delete-item-btn').on('click', '.delete-item-btn', function(ev) {
    var find_row = $(ev.target).closest('tr');
    $(ev.target).closest('tr').addClass('hide-row');
});

function waitForMatrixTableAndHide() {
    const $visibleMatrix = $("table.o_survey_question_matrix:visible");

    if ($visibleMatrix.length > 0) {
        $visibleMatrix.each(function () {
            const $rows = $(this).find("tbody > tr");

            if ($rows.length > 1) {
                $rows.addClass("hide-row");
                $rows.first().removeClass("hide-row");
            }
        });
    } else {
        // Retry again after delay, DOM probably not ready yet
        setTimeout(waitForMatrixTableAndHide, 50);
    }
}

// Triggered on survey page navigation
$(document).on("click", "button[type='submit'][value='next'], #next_page", function () {
    // Start loop after page changes
    setTimeout(waitForMatrixTableAndHide, 100);
});





SurveyFormWidget.include({

//    start() {
//        return this._super(...arguments).then(() => {
//            this._hideInitialMatrixRowsOnce();
//        });
//    },
//
//    _hideInitialMatrixRowsOnce() {
//        if (this._matrixHidden) return;
//
//        this.$("table.o_survey_question_matrix").each(function () {
//            const $rows = $(this).find("tbody > tr");
//            if ($rows.length > 1) {
//                $rows.addClass("hide-row");
//                $rows.first().removeClass("hide-row");
//            }
//        });
//        this._matrixHidden = true;
//    },

    _prepareSubmitAnswersMatrix: function (params, $matrixTable) {
        var self = this;
        const questionId = $matrixTable.data('name');

        $matrixTable.find('input:text').each(function () {
            params = self._prepareSubmitAnswerMatrixCustom(params, $matrixTable.data('name'), $(this).data('rowId'), $(this).data("col-id"), this.value);
        });

        $matrixTable.find('.sh_textarea').each(function () {
            params = self._prepareSubmitAnswerMatrixCustom(params, $matrixTable.data('name'), $(this).data('rowId'), $(this).data("col-id"), this.value);
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
