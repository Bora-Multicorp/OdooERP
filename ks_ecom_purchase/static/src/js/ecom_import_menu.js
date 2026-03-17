/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { exprToBoolean } from "@web/core/utils/strings";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

export class KsEcomImportMenu extends Component {
    static template = "ks_ecom_purchase.KsEcomImportMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    async openImportWizard() {
        const { context, resModel } = this.env.searchModel;
        await this.action.doAction("ks_ecom_purchase.action_ks_po_import_wizard", {
            additionalContext: {
                ...context,
                active_model: resModel,
            },
        });
    }

    async openReceiptImportWizard() {
        const { context, resModel } = this.env.searchModel;
        await this.action.doAction("ks_ecom_purchase.action_po_receipt_import_wizard", {
            additionalContext: {
                ...context,
                active_model: resModel,
            },
        });
    }

    async openRefundImportWizard() {
        const { context, resModel } = this.env.searchModel;
        await this.action.doAction("ks_ecom_purchase.action_po_refund_import_wizard", {
            additionalContext: {
                ...context,
                active_model: resModel,
            },
        });
    }
}

export const ksEcomImportMenuItem = {
    Component: KsEcomImportMenu,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, isSmall, searchModel }) =>
        !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        searchModel.resModel === "purchase.order" &&
        ["kanban", "list"].includes(config.viewType) &&
        exprToBoolean(config.viewArch.getAttribute("import"), true) &&
        exprToBoolean(config.viewArch.getAttribute("create"), true),
};

cogMenuRegistry.add("ks-ecom-import-menu", ksEcomImportMenuItem, { sequence: 2 });

