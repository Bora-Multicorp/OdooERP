/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";

patch(ListRenderer.prototype, {
    formatAggregate(column) {
        const value = super.formatAggregate(column);
        if (column.sum && typeof column.sum === "string" && column.sum !== "1" && column.sum !== "true" && value) {
            return `${column.sum} ${value}`;
        }
        return value;
    },
});
