/** @odoo-module **/

import { FormController } from "@web/views/form/form_controller";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

console.log("🔁 JS loaded: disable_inputs.js");

patch(FormController.prototype, {
    setup() {
        super.setup();
        console.log("🧠 FormController patched");

        const disableInputs = () => {
            console.log("✅ Disabling inputs for product.template");
            const inputs = document.querySelectorAll(
                ".o_form_view input, .o_form_view select, .o_form_view textarea, .o_form_view button"
            );
            inputs.forEach(input => {
                input.setAttribute("disabled", "true");
                input.classList.add("o_disabled");
            });
        };

        const observeTabs = () => {
            const tabContainer = document.querySelector('.nav-tabs');
            if (!tabContainer) {
                console.warn("⚠️ Tab container not found");
                return;
            }

            tabContainer.addEventListener('click', () => {
                console.log("📌 Tab switched");
                setTimeout(() => {
                    disableInputs();
                }, 300); // Delay to allow tab to load
            });
        };

        onMounted(() => {
            console.log("🚀 onMounted triggered");
            setTimeout(() => {
                disableInputs();
                observeTabs();
            }, 100); // allow DOM to render
        });
    },
});
