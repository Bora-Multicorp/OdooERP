/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

console.log("🔁 JS loaded: disable_inputs.js");

patch(FormController.prototype, {
    setup() {
        super.setup();
        console.log("🧠 FormController patched");

        const getCurrentState = () => {
            const activeStatusButton = document.querySelector('.o_statusbar_status .o_arrow_button[aria-current="step"]');
            if (activeStatusButton) {
                const value = activeStatusButton.dataset.value;
                console.log("🎯 Found statusbar state:", value);
                return value;
            } else {
                console.warn("⚠️ State button not found in statusbar yet");
            }

            return undefined;
        };

        const shouldDisableForm = () => {
            const value = getCurrentState();
            console.log("🔍 Current state value detected:", value);

            if (value === "pending" || value === "rejected" || value === "confirmed") {
                console.log(`⛔ Disabling form because state is "${value}"`);
                return true;
            } else {
                console.log(`✅ State is "${value}", form remains editable`);
                return false;
            }
        };

        const disableInputs = () => {
            console.log("🛑 Disabling all inputs");

            const inputs = document.querySelectorAll(
                "td.o_field_x2many_list_row_add a, .o_form_sheet .form-check-input, .o_form_sheet input, .o_form_sheet select, .o_form_sheet textarea, .o_form_sheet button"
            );
            inputs.forEach(input => {
                input.setAttribute("disabled", "true");
                input.classList.add("o_disabled");
            });

            document.querySelectorAll('.o_field_widget').forEach(cb => {
                cb.style.pointerEvents = "none";
                cb.classList.add("o_disabled");
            });

            const formSheet = document.querySelector('.o_form_sheet');
            if (formSheet) {
                formSheet.classList.add("o_form_state_disabled");
            }
        };

        const observeTabs = () => {
            const tabContainer = document.querySelector('.nav-tabs');
            if (!tabContainer) return;

            tabContainer.addEventListener('click', () => {
                console.log("🌀 Tab switched, checking state again...");
                setTimeout(() => {
                    if (shouldDisableForm()) {
                        disableInputs();
                    }
                }, 300);
            });
        };

        const waitForStateAndRun = () => {
            let attempts = 0;
            const interval = setInterval(() => {
                const value = getCurrentState();
                if (value || attempts > 20) {
                    clearInterval(interval);

                    if (value) {
                        console.log("✅ Final state loaded:", value);
                        if (shouldDisableForm()) {
                            disableInputs();
                        }
                        observeTabs();
                    } else {
                        console.warn("⚠️ Could not find state after 2s");
                    }
                }
                attempts++;
            }, 100);
        };

        onMounted(() => {
            console.log("🚀 onMounted triggered");
            waitForStateAndRun();
        });
    },
});
