/** @odoo-module **/

import { registry } from "@web/core/registry";

function switchToQcTab(env, action) {
    console.log("✅ Action triggered: switch_to_qc_tab", action);

    const tabName = action.params?.tab_name || "note";

    setTimeout(() => {
        const notebook = document.querySelector(".o_notebook");
        if (!notebook) {
            console.warn("⚠️ Notebook NOT found in DOM!");
            return;
        }

        // 🔍 Debug all available tabs
        const allTabs = notebook.querySelectorAll("a[data-bs-toggle='tab']");
        console.log("📋 Found tabs:", allTabs.length);
        allTabs.forEach((t, i) => {
            console.log(
                `Tab[${i}]: text="${t.innerText.trim()}", target="${t.getAttribute(
                    "data-bs-target"
                )}", href="${t.getAttribute("href")}"`
            );
        });

        // ✅ Try to match by id
        let tab =
            notebook.querySelector(
                `a[data-bs-toggle="tab"][data-bs-target="#${tabName}"]`
            ) ||
            notebook.querySelector(
                `a[data-bs-toggle="tab"][href="#${tabName}"]`
            );

        if (tab) {
            console.log(`✅ Tab "${tabName}" FOUND, activating...`);
            tab.click();
        } else {
            console.warn(`⚠️ Tab "${tabName}" NOT found in DOM!`);
        }
    }, 500); // give more time for UI to render
}

registry.category("actions").add("switch_to_qc_tab", switchToQcTab);
