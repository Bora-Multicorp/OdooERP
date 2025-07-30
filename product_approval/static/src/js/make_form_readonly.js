/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

console.log("🔁 JS loaded: disable_inputs.js");

patch(FormController.prototype, {
    setup() {
        super.setup();
        console.log("🧠 FormController patched");

        // Reference to the current model from the controller's props
        const currentModel = this.props.resModel;
        console.log("Current Model:", currentModel);

        // Define the target model you want to affect
        const targetModel = 'product.template';

        // ONLY PROCEED IF WE ARE ON THE TARGET MODEL
        if (currentModel !== targetModel) {
            console.log(`⏩ Skipping form disablement for model: ${currentModel}`);
            return; // Exit setup if not on the target model
        }

        // Get current state from statusbar
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

        // Check if form should be readonly
        const shouldDisableForm = () => {
            const value = getCurrentState();
            console.log("🔍 Current state value detected:", value);

            // 👇 ADD confirmed to the list here
            if (["pending", "rejected", "confirmed"].includes(value)) {
                console.log(`⛔ Disabling form because state is "${value}"`);
                return true;
            } else {
                console.log(`✅ State is "${value}", form remains editable`);
                return false;
            }
        };

        // Disable all form inputs — ONLY in main view, not inside modals
        const disableInputs = () => {
            console.log("🛑 Disabling all inputs (excluding modals)");

            const formSheets = document.querySelectorAll('.o_form_sheet');

            formSheets.forEach(formSheet => {
                // Skip if it's inside a modal
                if (formSheet.closest('.modal')) {
                    console.log("🟡 Skipping modal content");
                    return;
                }

                // Disable inputs, selects, textareas, checkboxes, buttons
                formSheet.querySelectorAll(
                    "td.o_field_x2many_list_row_add a, .form-check-input, input, select, textarea, button"
                ).forEach(input => {
                    input.setAttribute("disabled", "true");
                    input.classList.add("o_disabled");
                });

                // Prevent interaction with fields
                formSheet.querySelectorAll('.o_field_widget').forEach(cb => {
                    cb.style.pointerEvents = "none";
                    cb.classList.add("o_disabled");
                });

                formSheet.classList.add("o_form_state_disabled");
            });
        };

        // Handle tab switching (re-check state)
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

        // Re-check state if it changes live (after save or status change)
        const watchStateChanges = () => {
            const statusbar = document.querySelector(".o_statusbar_status");
            if (!statusbar) {
                console.warn("⚠️ Statusbar not found for observation");
                return;
            }

            const observer = new MutationObserver(() => {
                const value = getCurrentState();
                console.log("🔄 Statusbar updated. New state:", value);

                // 👇 Re-check with confirmed included
                if (["pending", "rejected", "confirmed"].includes(value)) {
                    disableInputs();
                }
            });

            observer.observe(statusbar, {
                childList: true,
                subtree: true,
                attributes: true,
            });

            console.log("👀 Watching statusbar for live changes");
        };

        // Wait for state to become available after initial load
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
                        console.warn("⚠️ Could not find state after waiting");
                    }
                }
                attempts++;
            }, 100);
        };

        // Trigger everything on mounted
        onMounted(() => {
            console.log("🚀 onMounted triggered");
            waitForStateAndRun();
            setTimeout(() => {
                watchStateChanges(); // ✅ live check after save
            }, 500);
        });
    },
});