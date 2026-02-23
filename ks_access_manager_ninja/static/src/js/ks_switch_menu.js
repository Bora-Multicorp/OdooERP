import { SwitchCompanyItem } from "@web/webclient/switch_company_menu/switch_company_item";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

patch(SwitchCompanyItem.prototype, {

    logIntoCompany() {
        let res = super.logIntoCompany(...arguments);
        this.clear_cache();
        return res
    },

    async clear_cache() {
        await rpc('/clear/cache', {});
    }



});
