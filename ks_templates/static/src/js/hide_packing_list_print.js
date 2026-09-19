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

        // Filter invoice (account.move) Download menu based on visibility conditions
        if (this.model.root.resModel === "account.move" && items?.print?.length) {
            const showCommercialInvoice = this.model.root.data.ks_show_commercial_invoice;
            const isCompIndian = Boolean(this.model.root.data.ks_is_company_indian);
            const isCustIndian = Boolean(this.model.root.data.ks_is_customer_indian);

            items.print = items.print.filter((item) => {
                const label = (
                    item.label ||
                    item.description ||
                    item.name ||
                    item.action?.name ||
                    item.action?.description ||
                    ""
                ).trim().toLowerCase();

                // Commercial Invoice visibility:
                // Hide when both company and customer are Indian; show otherwise
                if (label.includes("commercial invoice")) {
                    return showCommercialInvoice !== undefined ? Boolean(showCommercialInvoice) : !(isCompIndian && isCustIndian);
                }

                // Show all other reports (like Domestic Sales - Tax Invoice) unconditionally
                return true;
            });
        }

        return items;
    },
});
