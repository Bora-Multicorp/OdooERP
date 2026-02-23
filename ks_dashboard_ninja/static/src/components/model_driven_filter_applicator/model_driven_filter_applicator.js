/** @odoo-module **/

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { useBus } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useGetTreeDescription } from "@web/core/tree_editor/utils";
import { treeFromDomain } from "@web/core/tree_editor/condition_tree";
import { setObjectInCookie, getObjectFromCookie, eraseCookie } from "@ks_dashboard_ninja/js/cookies";
import { deepMerge } from "@web/core/utils/objects";
import { getSessionStorage, setSessionStorage, sessionKeys } from "@ks_dashboard_ninja/js/cookies";
import { useService } from "@web/core/utils/hooks";



export class ModelDrivenFilterApplicator extends Component {

    /*
        * This component is based on event bus
        * Takes any model name , group [ domain with key ]
        * Applies it to dashboard and maintains its facets
    */

    static template = "ks_dashboard_ninja.model_driven_filter_applicator"
    static props = {
        update: { type: Function },
        remove: { type: Function },
        isReset: { type: Boolean },
        options: { type: Object, optional: true },
    };
    static defaultProps = {
        options: {},
    };

    setup(){
        this.notification = useService('notification')
        this.getDomainTreeDescription = useGetTreeDescription();
        this.state = useState({
            facets: getSessionStorage(sessionKeys.mdfaFacets + this.props.options.ks_dashboard_id) ?? {}
        })


        useBus(this.env.bus, 'APPLY: Dashboard Filter', ({ detail }) => {
            const { model_display_name, model_name, field_name, operator, value } = detail
            this.addFilter(model_display_name, model_name, field_name, operator, value)
        })


//        onWillStart( () => this.apply_cookies_data() )
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps))
    }

    onPropsUpdated(nextProps){
        if(nextProps.isReset){
//            eraseCookie('ChartFilter' + this.props.options.ks_dashboard_id)
            this.reset()
        }
    }

//    apply_cookies_data(){
//        let facets_data = getObjectFromCookie('ChartFilter' + this.props.options.ks_dashboard_id)
//        this.state.facets = facets_data ?? {}
//    }

    reset(){
        this.state.facets = {}
        sessionStorage.removeItem(sessionKeys.mdfaFacets + this.props.options.ks_dashboard_id)
    }

//    async make_label(model, domain){
//        let label =
//        return label;
//    }

    async addFilter(modelDisplayName, model, fieldName, operator, value){

        sessionStorage.removeItem(sessionKeys.mdfaFacets + this.props.options.ks_dashboard_id)

        let groupKey = `${model + '_' + fieldName + operator + value}`

        if(this.state.facets[model]?.groups?.[groupKey])   return

        let domain = new Domain([[fieldName , operator, value]]).toList();
        let label = await this.getDomainTreeDescription(model, treeFromDomain(domain))

        let extension = {
            [model]: {
                groups: {
                    [groupKey]: { label, domain }
                },
                model_name: modelDisplayName
            }
        }

        this.state.facets = deepMerge(this.state.facets, extension)


        this.props.update({ [model]: { [groupKey]: domain}})
        setSessionStorage(sessionKeys.mdfaFacets + this.props.options.ks_dashboard_id, this.state.facets, this.notification)
//        let facets_to_update = this.state.facets[model] || {  }



//        facets_to_update.groups[groupKey] =
//        this.state.facets[model] = facets_to_update
//        this.apply_domain(model, groupKey, domain);
    }

    onRemoveFacet(model, group){
        /**
        * This method remove the facet or domain showing through facet from the dashboard
        */
        sessionStorage.removeItem(sessionKeys.mdfaFacets + this.props.options.ks_dashboard_id)
        delete this.state.facets[model].groups[group]

        if(!Object.values(this.state.facets[model].groups).length)  delete this.state.facets[model];
        this.props.remove({ [model]: { [group]: group}})
        setSessionStorage(sessionKeys.mdfaFacets + this.props.options.ks_dashboard_id, this.state.facets, this.notification)
    }


}
