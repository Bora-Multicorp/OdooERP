/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { exprToBoolean } from "@web/core/utils/strings";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

const cogMenuRegistry = registry.category("cogMenu");

export class KsEcomSaleImportMenu extends Component {
    static template = "ks_ecom_sales.KsEcomSaleImportMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.action = useService("action");
    }

    async openImportWizard() {
        const { context, resModel } = this.env.searchModel;
        await this.action.doAction("ks_ecom_sales.action_ks_so_import_wizard", {
            additionalContext: {
                ...context,
                active_model: resModel,
            },
        });
    }
}

export const ksEcomSaleImportMenuItem = {
    Component: KsEcomSaleImportMenu,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    isDisplayed: ({ config, isSmall, searchModel }) =>
        !isSmall &&
        config.actionType === "ir.actions.act_window" &&
        searchModel.resModel === "sale.order" &&
        ["kanban", "list"].includes(config.viewType) &&
        exprToBoolean(config.viewArch.getAttribute("import"), true) &&
        exprToBoolean(config.viewArch.getAttribute("create"), true),
};

cogMenuRegistry.add("ks-ecom-sale-import-menu", ksEcomSaleImportMenuItem, { sequence: 2 });
