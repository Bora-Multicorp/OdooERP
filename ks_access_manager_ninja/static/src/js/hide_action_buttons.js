/** @odoo-module **/

import {ActionMenus} from "@web/search/action_menus/action_menus";
let ks_action_registryId = 0;
export const STATIC_ACTIONS_GROUP_NUMBER = 1;
export const ACTIONS_GROUP_NUMBER = 100;

ActionMenus.prototype.getActionItems = async function(props){
    const ks_hide_actions = await this.orm.call("user.management", "ks_search_action_button", [1, this.props.resModel]);

    let ks_async_callback_Actions = (props.items.action || []).map((ks_action) =>
        Object.assign({ key: `action-${ks_action.description}` }, ks_action)
    );

    if(ks_hide_actions.length){
        ks_async_callback_Actions  = ks_async_callback_Actions.filter(val => {
            return !ks_hide_actions.includes(val.key);
        });
    }
    return (ks_async_callback_Actions || []).map((action) => {
            if (action.callback) {
                return Object.assign(
                    { key: `action-${action.description}`, groupNumber: ACTIONS_GROUP_NUMBER },
                    action
                );
            } else {
                return {
                    action,
                    description: action.name,
                    key: action.id,
                    groupNumber: action.groupNumber || ACTIONS_GROUP_NUMBER,
                };
            }
        });

}