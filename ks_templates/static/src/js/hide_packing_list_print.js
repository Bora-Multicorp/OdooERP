/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    async getActionMenuItems() {
        const items = await super.getActionMenuItems(...arguments);

        // Hide "Packing List" from non-outgoing stock pickings
        if (
            this.model.root.resModel === "stock.picking" &&
            items?.print?.length
        ) {
            const pickingTypeCode = this.model.root.data.picking_type_code;
            if (pickingTypeCode !== "outgoing") {
                items.print = items.print.filter((item) => {
                    const label = item.label || item.description || item.name || "";
                    return !label.toLowerCase().includes("packing list");
                });
            }
        }

        // Filter invoice (account.move) Download/Print menu based on company country
        if (this.model.root.resModel === "account.move") {
            const companyCountryCode = (this.model.root.data.ks_company_country_code || "").toUpperCase();
            const isIndianCompany = companyCountryCode === "IN";

            if (items?.print?.length) {
                items.print = items.print.filter((item) => {
                    const label = (item.label || item.description || item.name || "").trim().toLowerCase();
                    const isCommercialInvoice = label.includes("commercial invoice");

                    // Hide "Commercial Invoice" ONLY for Indian company (company_id's country is India)
                    if (isIndianCompany && isCommercialInvoice) {
                        return false;
                    }

                    return true;
                });
            }

            if (items?.action?.length && isIndianCompany) {
                items.action = items.action.filter((item) => {
                    const label = (item.label || item.description || item.name || "").trim().toLowerCase();
                    return !label.includes("commercial invoice");
                });
            }
        }

        return items;
    },
});
