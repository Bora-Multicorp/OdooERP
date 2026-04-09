/** @odoo-module **/
/**
 * KS Contact – Survey file prefill: mandatory bypass + JS remove without reload.
 */

import SurveyFormWidget from '@survey/js/survey_form';

SurveyFormWidget.include({

    events: Object.assign({}, SurveyFormWidget.prototype.events || {}, {
        'click .ks_remove_file_btn': '_ksOnRemoveFile',
    }),

    // -------------------------------------------------------------------------
    // Remove file card via JSON call — no page reload, no server validation flash
    // -------------------------------------------------------------------------

    _ksOnRemoveFile: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

        const btn = ev.currentTarget;
        const lineId = btn.dataset.lineId;
        const accessToken = btn.dataset.accessToken;

        if (!confirm('Remove this file?')) return;

        fetch('/survey/remove_file_answer/' + lineId, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: { access_token: accessToken },
            }),
        })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data.result && data.result.status === 'ok') {
                // Remove the card from DOM
                const card = btn.closest('.ks_file_chip');
                if (card) card.remove();

                // Check if any cards remain in this question's existing-files div
                const wrapper = btn.closest('.js_question-wrapper');
                if (!wrapper) return;

                const filesDiv = wrapper.querySelector('.ks_existing_files');
                const remainingCards = filesDiv ? filesDiv.querySelectorAll('.ks_file_chip') : [];

                if (remainingCards.length === 0) {
                    // No more existing files — remove sentinel, restore data-question-type
                    // on the file input so mandatory validation works normally again
                    if (filesDiv) filesDiv.remove();

                    const sentinel = wrapper.querySelector('.ks_file_existing_sentinel');
                    if (sentinel) sentinel.remove();

                    const fileInput = wrapper.querySelector('.sh_file_input');
                    if (fileInput) {
                        fileInput.setAttribute('data-question-type', 'que_sh_file');
                        fileInput.removeAttribute('data-has-existing');
                    }
                }
            } else {
                alert('Could not remove the file. Please try again.');
            }
        })
        .catch(function () {
            alert('Network error. Please try again.');
        });
    },

    // -------------------------------------------------------------------------
    // Bypass mandatory validation when existing files are present (sentinel)
    // -------------------------------------------------------------------------

    _validateForm: function ($form, formData) {
        const errors = this._super.apply(this, arguments);

        // The sentinel hidden input (value="existing") already satisfies
        // the `!$input.val()` check in the original loop, so errors should
        // never be added for those questions. This is a safety net.
        $form.find('.sh_file_input[data-has-existing]').each(function () {
            const questionId = String($(this).closest('.js_question-wrapper').attr('id'));
            if (questionId && errors[questionId]) {
                delete errors[questionId];
            }
        });

        return errors;
    },
});
