/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

console.log("🔁 JS loaded: disable_inputs.js");

patch(FormController.prototype, {
    setup() {
        super.setup();
        console.log("🧠 FormController patched");

        const shouldDisableForm = () => {
            const stateField = document.querySelector('[name="state"]');
            const value = stateField?.value;
            console.log("🔍 Current state:", value);
            return value === "pending" || value === "rejected";
        };

        const disableInputs = () => {
            console.log("✅ Disabling inputs for product.template");

            // Disable input, select, textarea, button
            const inputs = document.querySelectorAll(
                "td.o_field_x2many_list_row_add a, .o_form_sheet .form-check-input, .o_form_sheet input, .o_form_sheet select, .o_form_sheet textarea, .o_form_sheet button"
            );
            inputs.forEach(input => {
                input.setAttribute("disabled", "true");
                input.classList.add("o_disabled"); // Add only if in right state
            });

            // Disable pointer events
            document.querySelectorAll('.o_field_widget').forEach(cb => {
                cb.style.pointerEvents = "none";
                cb.classList.add("o_disabled"); // Optional: add class for styling
            });

            // Optional: Add a parent-level CSS hook
            const formSheet = document.querySelector('.o_form_sheet');
            if (formSheet) {
                formSheet.classList.add("o_form_state_disabled");
            }
        };

        const observeTabs = () => {
            const tabContainer = document.querySelector('.nav-tabs');
            if (!tabContainer) return;

            tabContainer.addEventListener('click', () => {
                setTimeout(() => {
                    if (shouldDisableForm()) {
                        disableInputs();
                    }
                }, 300);
            });
        };

        onMounted(() => {
            console.log("🚀 onMounted triggered");
            setTimeout(() => {
                if (shouldDisableForm()) {
                    disableInputs();
                }
                observeTabs();
            }, 100);
        });
    },
});
