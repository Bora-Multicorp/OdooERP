/** @odoo-module */
import publicWidget from "@web/legacy/js/public/public_widget";
import SurveyFormWidget from '@survey/js/survey_form';
import SurveyPreloadImageMixin from "@survey/js/survey_preload_image_mixin";
/**  Extends publicWidget to create "SurveyFormUpload" */
publicWidget.registry.SurveyFormUpload = publicWidget.Widget.extend(SurveyPreloadImageMixin, {
        selector: '.o_survey_form',
        events: {
            'change .o_survey_upload_file': '_onFileChange',
        },
        init() {
            this._super(...arguments);
//            this.rpc = this.bindService("rpc");
        },
        /** On adding file function */
        _onFileChange: function(event) {
    var self = this;
    var files = event.target.files;
    var fileNames = [];
    var dataURLs = [];

    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const reader = new FileReader();

        reader.onload = function(e) {
            const dataURL = e.target.result.split(',')[1];
            fileNames.push(file.name);
            dataURLs.push(dataURL);

            const $input = $(event.target);  // 🔧 Fix: use only current input
            $input.attr('data-oe-data', JSON.stringify(dataURLs));
            $input.attr('data-oe-file_name', JSON.stringify(fileNames));

            // Find the fileList div next to this input
            const $fileListContainer = $input.closest('.form-group').find('.fileList');
            if (!$fileListContainer.length) return;

            $fileListContainer.empty();  // clear previous contents

            const ul = $('<ul/>');
            fileNames.forEach(function(name) {
                ul.append($('<li/>').text(name));
            });

            const deleteBtn = $('<button type="button">Delete All</button>');
            deleteBtn.on('click', function() {
                $fileListContainer.empty();
                $input.attr('data-oe-data', '');
                $input.attr('data-oe-file_name', '');
                $input.val('');
            });

            $fileListContainer.append(ul, deleteBtn);
        };

        reader.readAsDataURL(file);
    }
},

    });
export default publicWidget.registry.SurveyFormUpload;
