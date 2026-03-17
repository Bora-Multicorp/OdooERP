/** @odoo-module **/

import { Component, useState, onWillUpdateProps, onWillStart, onRendered, toRaw } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useGetTreeDescription } from "@web/core/tree_editor/utils";
import { Domain } from "@web/core/domain";
import { treeFromDomain } from "@web/core/tree_editor/condition_tree";
import { setObjectInCookie, getObjectFromCookie, eraseCookie } from "@ks_dashboard_ninja/js/cookies";
import { deepMerge } from "@web/core/utils/objects";
import { deepCopy, omit } from "@web/core/utils/objects";
import { getSessionStorage, setSessionStorage, sessionKeys } from "@ks_dashboard_ninja/js/cookies";
import { useService } from "@web/core/utils/hooks";


export class DropDownWithItemsSearch extends Component{

    static template = "ks_dashboard_ninja.pre_defined_filter_dropdown"
    static props = {
        ddItems: { type: Array },
        ddItemSelect: { type: Function },
    };
    static components = { DropdownItem }

    setup(){
        this.state = useState({ searchText: '' });
    }

    get ddItems(){
        let searchedFilters = this.props.ddItems.filter(
            (item) => item.name.toLowerCase().includes(this.state.searchText.toLowerCase()) || item.type === 'separator')

        while(this.state.searchText && searchedFilters.length && searchedFilters[searchedFilters.length - 1].type === 'separator')
                searchedFilters.pop();

        while(this.state.searchText && searchedFilters.length && searchedFilters[0].type === 'separator')   searchedFilters.shift()

        return searchedFilters;
    }
}

export class PreDefinedFilter extends Component{
    static template = "ks_dashboard_ninja.pre_defined_filter"
    static props = {
        data: { type: Object },
        update: { type: Function, optional: true },
        isReset: { type: Boolean, optional: true },
        remove: { type: Function, optional: true },
        options: { type: Object, optional: true },  // Tobe used for extra data provides to the component
    };
    static defaultProps = {

    };
    static components = { Dropdown, DropDownWithItemsSearch }

    setup(){
        this.getDomainTreeDescription = useGetTreeDescription()

        this.notification = useService('notification')
        this.defaultFacet = { "Select Filter": { model_name: 'Select Filter', groups: {}} }
        this.state = useState({
            facets : getSessionStorage(sessionKeys.pfFacets + this.props.options.ks_dashboard_id)
                            || deepCopy(this.defaultFacet),
            data: this.props.data   // Predefined active filter data not gets updated on dashboard main data

        });

        onWillStart( () => {
            this.dataList = Object.values(this.props.data).sort(function(a, b){return a.sequence - b.sequence})

            let isStored = Object.keys(
                getSessionStorage(sessionKeys.dashboardDomainData + this.props.options.ks_dashboard_id)?.domainData ?? {}
            ).length

            if(!isStored)   this.setActiveFilters()
        })
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps))
    }

    onPropsUpdated(nextProps) {
        if(nextProps.isReset)
            this.reset()
    }

    setActiveFilters(){
        let ids = []
        Object.values(this.props.data).forEach((filter)=> {
            if(filter.active)   ids.push(filter.id)
        })

        if(ids.length)  this.addFilter(ids)
    }

    removeSessionStorage(){
        sessionStorage.removeItem(sessionKeys.pfFacets + this.props.options.ks_dashboard_id)
        sessionStorage.removeItem(sessionKeys.pfData + this.props.options.ks_dashboard_id)
    }

    setSessionStorage(){
        setSessionStorage(sessionKeys.pfFacets + this.props.options.ks_dashboard_id, this.state.facets, this.notification)
        setSessionStorage(sessionKeys.pfData + this.props.options.ks_dashboard_id, this.state.data, this.notification)
    }

    reset(){
        Object.values(this.state.data).forEach( (filter) => { filter.active = false })

        this.state.facets = deepCopy(this.defaultFacet)
        this.removeSessionStorage()
    }

    filterSelect(filter){
        let filterId = this.state.facets[filter.model]?.groups?.[filter.categ]?.ids?.[filter.id]

        if(filterId){
            this.removeFilter([filterId])
            return
        }
        this.addFilter([filter.id])
    }

    removeFilter(ids){
        this.removeSessionStorage()

        let modelSubDomains = {}
        ids.forEach( (id) => {
            let data = this.state.data[id]
            this.state.data[id].active = false

            delete this.state.facets[data.model].groups[data.categ].ids[id]

            let remainIds = Object.keys(this.state.facets[data.model].groups[data.categ].ids)

            if(remainIds.length){
                let domainList = remainIds.map( (id) => this.state.data[id].domain)
                let domain = Domain.or(domainList).toList()
                let label = this.makeLabel(remainIds)
                modelSubDomains[data.model] = {
                    [data.categ]: domain
                }

                Object.assign(this.state.facets[data.model].groups[data.categ], {
                    domain, label
                })
                this.update(modelSubDomains)
            }
            else{
                delete this.state.facets[data.model].groups[data.categ]
                this.remove({ [data.model]: { [data.categ]: data.domain }})
            }
        })

        this.refreshFacets()
        this.setSessionStorage()
    }

    addFilter(ids){
        this.removeSessionStorage()
        if (this.state.facets["Select Filter"])   delete this.state.facets["Select Filter"]

        let modelSubDomains = {}
        let facets = toRaw(this.state.facets)

        ids.forEach( (id) => {
            let data = this.state.data[id]

            let activeIds = Object.keys(facets[data.model]?.groups?.[data.categ]?.ids ?? {})
            let domainList = [id, ...activeIds].map( (id) => this.state.data[id].domain)
            let domain = Domain.or(domainList).toList()
            let label = this.makeLabel([id, ...activeIds])

            modelSubDomains[data.model] ??= {}
            modelSubDomains[data.model][data.categ] = domain

            let subExtension = {
                [data.model]: {
                    model_name: data.model_name,
                    groups: {
                        [data.categ]: {
                            label: label,
                            ids: { [id]: id },
                            domain: domain
                        }
                    }
                }
            }

            facets = deepMerge(facets, subExtension)
        })

        ids.forEach( (id) => {
            this.state.data[id].active = true
        })

        this.state.facets = facets
        this.update(modelSubDomains);
        this.setSessionStorage()

    }

    makeLabel(ids){
        let nameList = ids.map( (id) => this.state.data[id].name)
        return nameList.join(' or ')
    }

    update(modelSubDomains){
        this.setSessionStorage()
        this.props.update(modelSubDomains)
    }

    remove(modelSubDomains){
        this.props.remove(modelSubDomains)
    }

    refreshFacets(){
        Object.keys(this.state.facets).forEach( (model) => {
            if(!Object.keys(this.state.facets[model].groups).length)
                delete this.state.facets[model]

        })

        if(!Object.keys(this.state.facets).length)  this.state.facets = deepCopy(this.defaultFacet)
    }

    removeGroup(model, group){
        this.removeFilter(Object.keys(this.state.facets[model].groups[group].ids))
    }

}


