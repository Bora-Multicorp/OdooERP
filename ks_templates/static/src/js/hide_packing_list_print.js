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

        // Filter invoice (account.move) Download menu based on zone
        if (this.model.root.resModel === "account.move" && items?.print?.length) {
            const zone = this.model.root.data.ks_zone || "";
            const isIndia = zone.toLowerCase() === "india";

            items.print = items.print.filter((item) => {
                const label = (item.label || item.description || item.name || "").trim().toLowerCase();
                if (isIndia) {
                    // India zone: show only "With GST Report"
                    return label.includes("with gst");
                } else {
                    // Other zones: show "Commercial Invoice" and "Without GST Report", hide "PDF"
                    return label.includes("commercial invoice") || label.includes("without gst");
                }
            });
        }

        return items;
    },
});
