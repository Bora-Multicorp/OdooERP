/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { sessionKeys } from "@ks_dashboard_ninja/js/cookies";


patch(FormController.prototype,{

    async onRecordSaved(record, changes){

        if(this.model?.config?.resModel === 'ks_dashboard_ninja.board' && this.model.config.resId){

            let fieldNames = [ 'ks_dashboard_custom_filters_ids', 'ks_dashboard_defined_filters_ids',
                                'ks_date_filter_selection', 'ks_default_end_time', 'ks_dashboard_start_date',
                                'ks_dashboard_end_date' ]

            let isChange = fieldNames.some(field_name => changes.hasOwnProperty(field_name))

            if(isChange){
                Object.values(sessionKeys).forEach( (key) => {
                    sessionStorage.removeItem(key + this.model.config.resId)
                })
            }

        }
        super.onRecordSaved(record, changes);
    }
});




