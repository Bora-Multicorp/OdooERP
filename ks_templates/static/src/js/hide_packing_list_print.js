/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { AccountMoveFormController } from "@account/components/account_move_form/account_move_form";

// Patch AccountMoveFormController to prevent dynamic "PDF" extra print items from loading
if (AccountMoveFormController) {
    patch(AccountMoveFormController.prototype, {
        async loadExtraPrintItems() {
            return [];
        },
    });
}

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
            const zone = (this.model.root.data.ks_zone || "").toLowerCase();
            const isIndiaZone = zone === "india";
            const showCommercialInvoice = this.model.root.data.ks_show_commercial_invoice;
            const showDomesticTaxInvoice = this.model.root.data.ks_show_domestic_tax_invoice;
            const isCompIndian = Boolean(this.model.root.data.ks_is_company_indian);
            const isCustIndian = Boolean(this.model.root.data.ks_is_customer_indian);

            items.print = items.print.filter((item) => {
                const label = (item.label || item.description || item.name || "").trim().toLowerCase();
                const key = (item.key || "").toLowerCase();

                // Explicitly hide standard Odoo base PDF / Invoices report
                if (label === "pdf" || label === "invoices" || label === "invoice" || label.startsWith("pdf ") || label === "invoice pdf" || key === "download_pdf") {
                    return false;
                }

                // Commercial Invoice visibility:
                // 1. Non-Indian company => show
                // 2. Indian company + Indian customer => hide
                // 3. Indian company + Non-Indian customer => show
                if (label.includes("commercial invoice")) {
                    return showCommercialInvoice !== undefined ? Boolean(showCommercialInvoice) : !(isCompIndian && isCustIndian);
                }

                // Domestic Sales - Tax Invoice visibility:
                // 1. Indian company + Indian customer => show
                // 2. Otherwise => hide
                if (label.includes("domestic sales") || label.includes("tax invoice")) {
                    return showDomesticTaxInvoice !== undefined ? Boolean(showDomesticTaxInvoice) : (isCompIndian && isCustIndian);
                }

                if (isIndiaZone) {
                    // India zone: show "With GST Report"
                    return label.includes("with gst");
                } else {
                    // Other zones: show "Without GST Report"
                    return label.includes("without gst");
                }
            });
        }

        return items;
    },
});
