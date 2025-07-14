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

    const allowedTypes = [
        'image/jpeg', 'image/png', 'image/jpg', 'image/gif',
        'image/bmp', 'image/webp', 'image/svg+xml',
        'video/mp4', 'video/mpeg', 'video/ogg',
        'video/webm', 'video/avi', 'video/quicktime',
        'application/pdf'
    ];

    const allowedVideoTypes = [
        'video/mp4', 'video/mpeg', 'video/ogg',
        'video/webm', 'video/avi', 'video/quicktime'
    ];

    // 🔍 Detect question label text
    const labelText = $(event.target)
        .closest('.js_question-wrapper')
        .find('.o_survey_question_title, h3 span')
        .first()
        .text()
        .trim();

    const isVideoOnly = labelText.toLowerCase().includes('shop videos');

    for (let i = 0; i < files.length; i++) {
        const file = files[i];

        // 🔒 Restrict to videos only for "Shop Videos" field
        if (isVideoOnly && !allowedVideoTypes.includes(file.type)) {
            alert(`Invalid file type for "${labelText}". Only video files are allowed.`);
            event.target.value = ''; // Reset the input
            return;
        }

        // ✅ Basic allowed file types validation
        if (!allowedTypes.includes(file.type)) {
            alert(`Invalid file type: ${file.name}\n\nOnly images, videos, and PDFs are allowed.`);
            event.target.value = ''; // Reset input
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            const dataURL = e.target.result.split(',')[1];
            fileNames.push(file.name);
            dataURLs.push(dataURL);

            const $input = $(event.target);
            $input.attr('data-oe-data', JSON.stringify(dataURLs));
            $input.attr('data-oe-file_name', JSON.stringify(fileNames));

            const $fileListContainer = $input.closest('.form-group').find('.fileList');
            if (!$fileListContainer.length) return;

            $fileListContainer.empty();

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
