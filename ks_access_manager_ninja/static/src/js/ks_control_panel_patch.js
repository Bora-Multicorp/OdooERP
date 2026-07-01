/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { patch } from "@web/core/utils/patch";
import { onMounted, onPatched, onWillStart } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";


patch(ControlPanel.prototype, {
    setup() {
        super.setup();
        this.ksHideUploadChecked = false;
        this.ksHideUpload = false;
        
        onWillStart(async () => {
            await this.checkHideUpload();
        });
        
        onMounted(() => {
            if (this.ksHideUpload) {
                this._hideUploadButtonsInDOM();
            }
        });
        
        onPatched(() => {
            if (this.ksHideUpload) {
                this._hideUploadButtonsInDOM();
            }
        });
    },

    async checkHideUpload() {
        const model = this.env.config?.resModel || this.env.searchModel?.resModel;
        if (!model || this.ksHideUploadChecked) {
            return;
        }

        // Add CSS immediately before RPC to prevent flash
        this._addHideUploadCSS();

        try {
            const HideUpload = await rpc('/web/dataset/call_kw', {
                model: 'user.management',
                method: 'ks_search_hide_upload_button',
                args: [1, model],
                kwargs: {},
            });

            this.ksHideUploadChecked = true;
            this.ksHideUpload = HideUpload;

            if (!HideUpload) {
                // Remove CSS if upload shouldn't be hidden
                this._removeHideUploadCSS();
            }
        } catch (error) {
            console.warn('Error checking upload button hide:', error);
            this._removeHideUploadCSS();
        }
    },

    _addHideUploadCSS() {
        const model = this.env.config?.resModel || this.env.searchModel?.resModel;
        const styleId = `ks_hide_upload_${model || 'global'}`;
        if (!document.getElementById(styleId)) {
            const style = document.createElement("style");
            style.id = styleId;
            style.innerHTML = `
                /* Hide upload buttons in control panel */
                .o_control_panel .o_button_upload_bill,
                .o_control_panel .o_button_upload_expense,
                .o_control_panel .o_widget_account_file_uploader,
                .o_control_panel .o_widget_purchase_file_uploader,
                .o_control_panel .o_list_button_upload,
                .o_control_panel button[class*="upload"],
                .o_control_panel button[class*="Upload"] {
                    display: none !important;
                }
            `;
            document.head.appendChild(style);
        }
    },

    _removeHideUploadCSS() {
        const model = this.env.config?.resModel || this.env.searchModel?.resModel;
        const styleId = `ks_hide_upload_${model || 'global'}`;
        const styleEl = document.getElementById(styleId);
        if (styleEl) {
            styleEl.remove();
        }
    },

    _hideUploadButtonsInDOM() {
        const controlPanel = this.root?.el;
        if (!controlPanel) return;

        // Find all buttons in control panel
        const allButtons = controlPanel.querySelectorAll('button, a.btn');

        allButtons.forEach(el => {
            if (el.hasAttribute('data-ks-upload-hidden') ||
                el.hasAttribute('data-ks-allow-upload')) {
                return;
            }

            if (el.closest('.o_field_widget') ||
                el.closest('.o_field_binary') ||
                el.closest('.FileUploader')) {
                return;
            }

            const text = (el.textContent || '').trim().toLowerCase();
            const title = (el.getAttribute('title') || '').toLowerCase();
            const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();

            // Only hide if text is exactly "upload" or starts with "upload "
            const isUploadButton = text === 'upload' ||
                                 text.startsWith('upload ') ||
                                 text === 'upload bill' ||
                                 text === 'upload pdf' ||
                                 (text.includes('upload') && (title.includes('upload') || ariaLabel.includes('upload')));

            // Hide upload buttons in control panel
            if (isUploadButton &&
                !text.includes('your file') &&
                text.length < 50) {
                el.style.setProperty('display', 'none', 'important');
                el.setAttribute('data-ks-upload-hidden', 'true');
            }
        });
    },
});


