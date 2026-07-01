
import {
    Component, useState, useEffect, onMounted, onWillUpdateProps, useRef, status, onRendered, onWillUnmount
} from "@odoo/owl"
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { DNTile } from '../ks_dashboard_tile_view/ks_dashboard_tile';
import { DNTodo } from '../ks_dashboard_to_do_item/ks_dashboard_to_do';
import { DNKpi } from '../ks_dashboard_kpi_view/ks_dashboard_kpi';
import { DNGraph } from '../ks_dashboard_graphs/ks_dashboard_graphs';
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";
import { useBus } from "@web/core/utils/hooks";
import { DNUseRef } from '@ks_dashboard_ninja/js/dn_utils';



// TODO: this component should be independent of the dashboard Data means if dashboard data is not passed it should still work
// TODO: while triggering the event to fetch item data , event key is  same if multiple same item in screen - handle this

export class KsItems extends Component {

    static template = "ks_dashboard_ninja.items_view"
    static components = { DNTile, DNTodo, DNKpi, DNGraph }
    static props = {
        itemsBasicData: {
            type: Array,
            optional: true
        },
        dashboardData: {
            type: [Object, Boolean],
            optional: true
        },
        filtersConfig: {
            type: [Object, Boolean],
            optional: true
        },
        dateFilterConfig: {
            type: [Object, Boolean],
            optional: true
        },
        isItemsPreview: { type: Boolean, optional: true },
        isGridStack: { type: Boolean },
        gsRootRef: { type: Function, optional: true },
        isAIExplanation: { type: Boolean, optional: true },
        isRowStructure: { type: Boolean, optional: true },
        isGridStructure: { type: Boolean, optional: true },
        isColumnStructure: { type: [Boolean, Object], optional: true },
        DNGridStack: { type: Object, optional: true },
        dnStore: { type: Object, optional: true },
    }


    setup(){
        this.actionService = useService('action')
        this.orm = useService('orm')

        this.gsRootRef = useForwardRefToParent("gsRootRef")
        this.rootRef = useRef("rootRef")

        this.DNUseRef = DNUseRef()
        this.state = useState({
            gridSelectedIds: new Set(),
        })


        onMounted( () => {
            if(this.props.isGridStack && this.props.DNGridStack)    this.gsInitiate()
        })

        this.debouncedModels = []

        useEffect( () => {
            let interval = parseInt(this.props.dashboardData?.ks_set_interval)

            if(!interval)   return;

            this._debouncedTriggerFetching = debounce(this.triggerFetching.bind(this), interval)
            const cb = (detail) =>  {
                this.debouncedModels.push(detail.model)
                this._debouncedTriggerFetching(detail)
            }

            this.env.services.bus_service.subscribe('Update: Dashboard Items', cb)
            return this.env.services.bus_service.removeEventListener('Update: Dashboard Items', cb)
        }, ()=>[])


        this.useEffectActions = []

        if(this.env.KsItemsEventName){
            useBus( this.env.bus, `${this.env.KsItemsEventName}`, ({ detail }) =>  {
                this.useEffectActions.push(...(detail.useEffectActions ?? []))
            })
        }

        useEffect(() => this.checkUseEffectActions())

        this.initializeObserver()

        useEffect( () => {
            for(let data of this.props.itemsBasicData){
                const el = this.DNUseRef.getEl(data.id)
                this.dnObserver.observeItem(el, data)
            }
            /*
            * Id as a html attribute should be there in elements with class 'grid-stack-item'
            */

         }, () => [])

        onWillUnmount( () => {
            this.dnObserver.observer.disconnect()
        })
    }

    get defaultLayout(){
        return this.props.dashboardData.gs_layouts_info.defaultLayout
    }

    initializeObserver() {
        const options = { threshold: 0.1 }

        this.dnObserver = {
            observer: new IntersectionObserver(this.observerCallback.bind(this), options),
            visibleItemSet: new Set(),
            metaData: new WeakMap(),
            observeItem(el, itemBasicData) {
                this.observer.observe(el)
                this.metaData.set(el, itemBasicData)
            }
        }
    }

    observerCallback(entries) {
        entries.forEach(entry => {
            let itemBasicData = this.dnObserver.metaData.get(entry.target)
            if (entry.isIntersecting) {
                this.dnObserver.visibleItemSet.add(itemBasicData.id)
                this.env.bus.trigger(`item_${itemBasicData.id}`, {})
            }
            else{
                this.dnObserver.visibleItemSet.delete(itemBasicData.id)
            }
        })
    }

    checkUseEffectActions() {
        while (this.useEffectActions.length > 0) {
            let action = this.useEffectActions.shift();

            if (action.type === 'addGsItem') {
                let itemEl = this.DNUseRef.getEl(action.itemBasicData.id);

                this.props.DNGridStack.makeGsItem(
                    itemEl, this.defaultLayout.grid_stack_config, action.itemBasicData
                );
                this.dnObserver.observeItem(itemEl, action.itemBasicData);
            } else if (action.type === 'updateGsItem') {
                let itemEl = this.DNUseRef.getEl(action.itemBasicData.id);

                this.props.DNGridStack.updateGridEl(itemEl, this.defaultLayout.grid_stack_config, action.itemBasicData);
                this.props.DNGridStack.saveLayout(this.defaultLayout);
                this.env.bus.trigger(`item_${action.itemBasicData.id}`, { isForced: true });
            }
        }
    }

    gsInitiate() {
        const gridStackOptions = {
            staticGrid: true,
            float: false,
            auto: false,
            cellHeight: 68,
            styleInHead : true,
            disableOneColumnMode: !isMobileOS(),
        }

        this.props.DNGridStack.gsInit(this.gsRootRef.el, gridStackOptions)


        // TODO: what if previous gridstack field doesn't have the config
        this.props.DNGridStack.gridStack.batchUpdate(true)

        for(let data of this.props.itemsBasicData){
            const el = this.DNUseRef.getEl(data.id)
            this.props.DNGridStack.makeGsItem(el, this.defaultLayout.grid_stack_config, data)
        }
        this.props.DNGridStack.gridStack.batchUpdate(false)
    }

    gridSelectOne(itemId){
        this.state.gridSelectedIds.has(itemId)
            ? this.state.gridSelectedIds.delete(itemId) : this.state.gridSelectedIds.add(itemId)
    }

    gridSelectAll(){
            if(this.props.itemsBasicData.length === this.state.gridSelectedIds.size){
            this.state.gridSelectedIds.clear()
            return
        }

        const ids = this.props.itemsBasicData.map((data) => data.id)
        this.state.gridSelectedIds = new Set([...this.state.gridSelectedIds, ...ids])
    }

    async onSaveGrid(){
        let promises = []
        let itemsDataToAdd = []

        let changedDashboardId = this.actionService.currentController.action.params.ks_dashboard_id

        for(const id of this.state.gridSelectedIds){
            delete this.props.dnStore.delete(id)
            let data = this.props.itemsBasicData.find( (itemBasicData) => itemBasicData.id == id)
            itemsDataToAdd.push(data)

            const vals = { ks_dashboard_ninja_board_id: changedDashboardId }

            promises.push(this.orm.write('ks_dashboard_ninja.item', [id], vals))
        }

        await Promise.all(promises)

        this.env.bus.trigger('MODIFY: Dashboard ITEM', { isAdd: true, itemsDataToAdd })
        this.env.dialogData?.close?.()

        await this.orm.unlink('ks_dashboard_ninja.board', [this.props.dashboardData.id])
    }


    triggerFetching(detail){

        // todo ?? should be we manage model-item-relation to remove this for loop
        for(let itemBasicData of this.props.itemsBasicData){

            let isForced = this.dnObserver.visibleItemSet.has(itemBasicData.id)

            if(this.debouncedModels.includes(itemBasicData.ks_model_name) || this.debouncedModels.includes(itemBasicData.ks_model_name_2)){
                this.props.dnStore.delete(itemBasicData.id)
                this.env.bus.trigger(`item_${itemBasicData.id}`, { isForced, allowItemFetching: !isForced })
            }

        }
        this.debouncedModels = []

    }

    _onKsItemClick(item_id){

    }

}

