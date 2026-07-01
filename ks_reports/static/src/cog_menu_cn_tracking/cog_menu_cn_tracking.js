/** @odoo-module **/

import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { STATIC_ACTIONS_GROUP_NUMBER } from "@web/search/action_menus/action_menus";

import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

/**
 * CN Tracking - cog menu item for Credit Notes list view.
 * Appears under Export All in the gear dropdown; runs the CN Tracking XLSX report.
 */
class CnTrackingCogMenu extends Component {
    static template = "ks_reports.CnTrackingCogMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
    }

    async onCnTracking() {
        let actionId = null;
        try {
            const [model, resId] = await this.orm.call(
                "ir.model.data",
                "check_object_reference",
                ["ks_reports", "action_cn_tracking_report_from_credit_notes"]
            );
            if (resId) {
                actionId = resId;
            }
        } catch {
            // action not found or no access
        }
        if (!actionId) {
            return;
        }
        const root = this.env.model?.root;
        const activeIds = root?.selection?.length
            ? root.selection.map((r) => r.resId)
            : [];
        await this.actionService.doAction(actionId, {
            additionalContext: {
                active_model: this.env.config.resModel,
                active_ids: activeIds,
                active_id: activeIds[0] || false,
            },
        });
    }
}

export const cnTrackingCogMenuItem = {
    Component: CnTrackingCogMenu,
    groupNumber: STATIC_ACTIONS_GROUP_NUMBER,
    sequence: 15,
    isDisplayed: (env) => {
        if (env.config?.resModel !== "account.move" || env.config?.viewType !== "list") {
            return false;
        }
        const ctx = env.config?.context || {};
        return ctx.search_default_out_refund === 1 || ctx.default_move_type === "out_refund";
    },
};

cogMenuRegistry.add("cn-tracking-menu", cnTrackingCogMenuItem);
