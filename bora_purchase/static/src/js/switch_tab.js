/** @odoo-module **/

import { registry } from "@web/core/registry";

function switchToQcTab(env, action) {

    const tabName = action.params?.tab_name;

    setTimeout(() => {
        const notebook = document.querySelector(".o_notebook");
        if (!notebook) {
            console.warn("⚠️ Notebook NOT found in DOM!");
            return;
        }
        // document.querySelector('.nav-tabs li:last-child a').click();
        const allTabs = notebook.querySelectorAll(".nav-tabs li a");
        // console.log("📋 Found tabs:", allTabs.length);
        // allTabs.forEach((t, i) => {
        //     console.log(
        //         `Tab[${i}]: text="${t.innerText.trim()}", target="${t.getAttribute(
        //             "data-bs-target"
        //         )}", href="${t.getAttribute("href")}"`
        //     );
        // });


        let tabName = (action.params?.tab_name || "").trim().toLowerCase();
        let tab = Array.from(allTabs).find(
            t => t.innerText.trim().toLowerCase() === tabName
        );
        if (tab) {
            tab.click();
        } else {
            console.warn(`⚠️ Tab "${tabName}" NOT found in DOM!`);
        }
    }, 500); // give more time for UI to render
}

registry.category("actions").add("switch_to_qc_tab", switchToQcTab);
