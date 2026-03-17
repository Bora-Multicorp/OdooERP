/** @odoo-module **/

import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { registry } from "@web/core/registry";
const cogMenuRegistry = registry.category("cogMenu");

CogMenu.prototype._registryItems = async function(){
    let model;
    try {
      model = this.env.config['viewId'];
    } catch (error) {}
    const ks_hide_spread_action = await this.orm.call("user.management", "ks_search_spread_button", [1, model]);

    let items = [];
    for (const item of cogMenuRegistry.getAll()) {
        if ("isDisplayed" in item ? await item.isDisplayed(this.env) : true) {
            items.push({
                Component: item.Component,
                groupNumber: item.groupNumber,
                key: item.Component.name,
            });
        }
    }
    if(ks_hide_spread_action.length){
        items  = items.filter(val => {
            return !ks_hide_spread_action.includes(val.key);
        });
    }
    return items;

}
