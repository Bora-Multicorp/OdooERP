/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { PreDefinedFilter } from "@ks_dashboard_ninja/components/predefined_filter/predefined_filter";
import { FavFilterWizard, FavouriteFilter } from "@ks_dashboard_ninja/components/favourite_filter/favourite_filter";
import { Domain } from "@web/core/domain";
import { CustomFilter } from '@ks_dashboard_ninja/components/custom_filter/custom_filter';
import { ModelDrivenFilterApplicator } from '@ks_dashboard_ninja/components/model_driven_filter_applicator/model_driven_filter_applicator';
import { setObjectInCookie, getObjectFromCookie, eraseCookie } from "@ks_dashboard_ninja/js/cookies";
import { deepMerge } from "@web/core/utils/objects";
import { deepCopy } from "@web/core/utils/objects";
import { useService } from "@web/core/utils/hooks";
import { getSessionStorage, setSessionStorage, sessionKeys } from "@ks_dashboard_ninja/js/cookies";
import { _t } from "@web/core/l10n/translation";


export class DNFilter extends Component{

    static props = {
        dashboardData: { type: Object },
        update: { type: Function },
    }
    static components = { PreDefinedFilter, Dropdown, CustomFilter, FavouriteFilter, ModelDrivenFilterApplicator }

    setup(){
        this.orm = useService('orm')
        this.notification = useService('notification')
        this.subDomainData = getSessionStorage(sessionKeys.subDomainData + this.props.dashboardData.id) || {}
        this.domainData = getSessionStorage(sessionKeys.domainData + this.props.dashboardData.id) || {}

        // todo: conditionally visible required ??
        this.isShowCustomFilter = Object.keys(this.props.dashboardData.ks_dashboard_custom_domain_filter).length

        this.state = useState({
            favFilterData: this.props.dashboardData.ks_dashboard_favourite_filter,
            resetAll: false,
            filtersCount: 0,
        })
        onWillStart( this.willStart );
    }

    willStart(){
        this.state.filtersCount = this.filtersCount
    }

    get options(){
        return {
            ks_dashboard_id : this.props.dashboardData.id,
        }
    }

    get filtersCount(){
        let count = 0

        Object.values(this.subDomainData).forEach( (modelSubDomainData) => {
            Object.keys(modelSubDomainData).forEach( (key) => {
                if(!key.startsWith('FF'))   ++count
            })
        })
        return count;
    }

    updateSubDomains(modelSubDomains){
        let extension = {}

        Object.keys(modelSubDomains).forEach( (model) => {
            Object.keys(modelSubDomains[model]).forEach( (key) => {
                extension[model] ??= {}
                extension[model][key] = modelSubDomains[model][key]
            })
        })

        this.subDomainData = deepMerge(this.subDomainData, extension)
        this.update(Object.keys(modelSubDomains))
    }

    clearRetention(){
        Object.values(sessionKeys).forEach( (key) => {
            sessionStorage.removeItem(key + this.props.dashboardData.id)
        })
        this.notification.add(_t("Filter Retention Cleared !!"), { type: "info" })
    }

    removeSessionStorage(){
        sessionStorage.removeItem(sessionKeys.subDomainData + this.props.dashboardData.id)
        sessionStorage.removeItem(sessionKeys.domainData + this.props.dashboardData.id)
    }

    setSessionStorage(){
        setSessionStorage(sessionKeys.subDomainData + this.props.dashboardData.id, this.subDomainData, this.notification)
        setSessionStorage(sessionKeys.domainData + this.props.dashboardData.id, this.domainData, this.notification)
    }

    hideFilterTab() {
        Collapse.getInstance('#collapseExample').hide()
    }

    removeSubDomains(modelSubDomains){
        Object.keys(modelSubDomains).forEach( (model) => {
            Object.keys(modelSubDomains[model]).forEach( (key) => {
                delete this.subDomainData[model][key]

                if(!Object.keys(this.subDomainData[model]).length)
                    delete this.subDomainData[model]
            })
        })

        this.update(Object.keys(modelSubDomains))
    }

    update(models){
        this.removeSessionStorage()

        for( let model of models){
            let domain = Domain.and([ ...Object.values(this.subDomainData[model] ?? {}) ]).toList()

            if(this.subDomainData[model]){
                this.domainData[model] = domain
            }
            else{
                delete this.domainData[model]
            }
        }

        this.setSessionStorage()
        this.state.filtersCount = this.filtersCount
        this.state.resetAll = false
        this.props.update(models, this.domainData)
    }

    reset(){
        this.domainData = {}
        this.subDomainData = {}
    }

    applyFavouriteFilter(modelSubDomains){
        this.reset()
        this.updateSubDomains(modelSubDomains)
        Object.assign(this.state, { filtersCount: 0, resetAll: true })
    }

    saveNewFavFilter(){
        this.env.services.dialog.add(FavFilterWizard,{
            addFavFilterData: this.addFavFilterData.bind(this),
        })
    }

    async addFavFilterData(data){
        Object.assign(data, {
            ks_dashboard_board_id: this.props.dashboardData.id,
            ks_filter: JSON.stringify(this.domainData)
        })
        let id = await this.orm.create('ks_dashboard_ninja.favourite_filters', [data])
        data.id = id[0]
        data.ks_filter = this.domainData
        this.state.favFilterData[id] = data
    }

    deleteFavFilter(id){
        delete this.state.favFilterData[id]
    }

}

DNFilter.template = "ks_dashboard_ninja.dn_filter"


