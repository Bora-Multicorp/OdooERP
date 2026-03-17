import { _t } from "@web/core/l10n/translation";
import { Component, onRendered, onWillStart, useState, onPatched, useChildSubEnv, useSubEnv, onWillUnmount,
            onMounted, onWillRender, onWillPatch, useRef, useEffect,  reactive, markRaw } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService, useBus } from "@web/core/utils/hooks";
import { localization } from "@web/core/l10n/localization";
import { session } from "@web/session";
import { download } from "@web/core/network/download";
import { useChildRef } from "@web/core/utils/hooks";
import { BlockUI } from "@web/core/ui/block_ui";
import { WebClient } from "@web/webclient/webclient";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { patch } from "@web/core/utils/patch";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { loadBundle } from '@web/core/assets';
import { FormViewDialog} from '@web/views/view_dialogs/form_view_dialog';
import { renderToElement } from "@web/core/utils/render";
import { deepCopy } from "@web/core/utils/objects";
import { convert_data_to_utc, eraseAllCookies } from '@ks_dashboard_ninja/js/dn_utils'
import { DNGridStack } from '@ks_dashboard_ninja/js/gsUtils'
import { DateTimePicker } from "@web/core/datetime/datetime_picker";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
const { DateTime } = luxon;
import {formatDate,formatDateTime} from "@web/core/l10n/dates";
import {parseDateTime,parseDate,} from "@web/core/l10n/dates";
import { KsHeader } from '@ks_dashboard_ninja/components/Header/Header'
import { KsItems } from "@ks_dashboard_ninja/components/ks_items/ks_items";
import { setObjectInCookie, getObjectFromCookie, eraseCookie } from "@ks_dashboard_ninja/js/cookies";
import { DNDashboardStore } from "@ks_dashboard_ninja/js/dn_store";
import { debounce } from "@bus/workers/websocket_worker_utils";
import { getSessionStorage, setSessionStorage, sessionKeys } from "@ks_dashboard_ninja/js/cookies";


export class KsDashboardNinja extends Component {

    static components = { KsHeader, KsItems };
    static template = "ks_dashboard_ninja.dashboard_view"

    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.rootRef = useRef("rootRef");

        this.ks_dashboard_id = this.props.action.params.ks_dashboard_id;
        this.isReloadOnFirstCreate = this.props.action?.params?.isReloadOnFirstCreate ? true : false

        this.state = useState({
            dashboardData: false,
            filtersConfig: getSessionStorage(sessionKeys.dashboardDomainData + this.ks_dashboard_id) || false,
            dateFilterConfig: getSessionStorage(sessionKeys.dateFilter + this.ks_dashboard_id) || false,
            itemsBasicData: false,      // should be a Array[] when assigned
            gsLayoutsInfo: false,
            is_loading: false
        })


        this.dnStore = new DNDashboardStore(this.orm)


        this.gsRootRef = useChildRef()

        onWillStart(this.willStart);

        this.env.services.bus_service.addChannel('ks_notification')

        //TODO: put dataFetching in useffect for loading animation and make dashboard  feasable for opening in modal

        useEffect(() => {

            }, ()=>[]
        )

        // TODO: remove deepcopy also - wjhat if object have some fucntions or circular refs


        onRendered(()=>{

            if(this.isReloadOnFirstCreate){
                this.isReloadOnFirstCreate = false;
                if(this.props.action.params && this.props.action.params.isReloadOnFirstCreate)
                    this.props.action.params.isReloadOnFirstCreate = false
                this.env.services.menu.reload();
                this.notification.add(_t('New Dashboard is successfully created'), { title: _t("New Dashboard"), type: 'success' });
            }
        })

//        useBus(this.env.bus, "GET:ParamsForItemFetch", (ev) => this.ksGetParamsForItemFetch(ev.detail));
        // TODO: make items independent , graph component,etc  should not be dependent on some other components,
        // TODO: presently we are using many functions in env , can be removed to make component fully independent

        useBus(this.env.bus, 'MODIFY: Dashboard ITEM', ({ detail }) => {
            if(detail.isAdd)        this.addItem(detail.itemsDataToAdd)
            else if(detail.isRemove)   this.removeItem(detail.itemDataToRemove)
            else if(detail.isUpdate)   this.updateItem(detail.itemsDataToUpdate)
        })

        this.KsItemsEventName = 'KS: UseEffectActions'

        useChildSubEnv({
            KsItemsEventName: this.KsItemsEventName
        })

        onMounted(() => {
            // FOR ARC Theme
            if(document.body.classList.contains("ks_body_class")){
                document.querySelector(".ks-zoom-view")?.classList.add("d-none")
            }
        })

        onWillUnmount( () => {
            // FOR ARC Theme
            document.querySelector(".ks-zoom-view")?.classList.remove("d-none")
            this.env.services.bus_service.deleteChannel('ks_notification')
            delete this.dnStore
            delete this.DNGridStack
        })

    }

    get isMobile(){
        return isMobileOS();
    }


    async willStart(){
        await loadBundle("ks_dashboard_ninja.ks_dashboard_lib")
        await this.fetchDashboardConfigs()

        let predefinedFilterData = getSessionStorage(sessionKeys.pfData + this.state.dashboardData.id)

        if(predefinedFilterData)
            this.state.dashboardData.ks_dashboard_pre_domain_filter = predefinedFilterData

        this.DNGridStack = new DNGridStack(this.orm)
    }

    sortItems(itemsBasicData, gsConfig){
        /*
        * It sorts the Items Basic Data List based on the y axis value of grid-stack configurations
        */
        let gsEntries = Object.entries(gsConfig)

        gsEntries.sort(function(a, b) {
            return (35 * a[1].y + a[1].x) - (35 * b[1].y + b[1].x);
        })

        let result = []
        let ids = []
        for( let gsEntry of gsEntries ){
            let itemBasicData = itemsBasicData.find( (itemBasicData) => itemBasicData.id == gsEntry[0])

            if(itemBasicData){
                ids.push(gsEntry[0])
                result.push(itemBasicData)
            }
        }

        itemsBasicData = itemsBasicData.filter((itemBasicData) => !ids.includes(String(itemBasicData.id)))

        return [...result, ...itemsBasicData]
    }

    setGsLayoutsInfo(layoutsInfo){
        return {
            gs_layouts: layoutsInfo.gs_layouts,
            multiLayout: layoutsInfo.multi_layouts,
            get defaultLayout() {
                if(this.multiLayout){
                    return this.gs_layouts.find(layout => layout.is_default) ?? this.gs_layouts[0] ?? {}
                }
                return this.mainLayout
            },
            get mainLayout() {
                return this.gs_layouts.find(layout => layout.is_main_layout) ?? this.gs_layouts[0] ?? {}
            },
            setGsLayouts(layouts){
                this.gs_layouts = layouts
            }
        }
    }

    async fetchDashboardConfigs(){
        // TODO: context to be used???
        let result = await this.orm.call(
            'ks_dashboard_ninja.board' , 'ks_fetch_dashboard_configs', [[this.ks_dashboard_id]], {}
        )

        result.dashboard_data.gs_layouts_info = this.setGsLayoutsInfo(result.gs_layouts_info)
        let itemsBasicData = this.sortItems(
            result.items_basic_data, result.dashboard_data.gs_layouts_info.defaultLayout.grid_stack_config
        )

        Object.defineProperty(this, 'isDashboardManager', {
            value: await user.hasGroup('ks_dashboard_ninja.ks_dashboard_ninja_group_manager'),
            writable : false,
            enumerable : true,
            configurable : false
        })

        Object.assign(this.state, {
            itemsBasicData: itemsBasicData,
            dashboardData: markRaw(result.dashboard_data),
        })
    }

    get dashboardActions(){
        return {
            addItem: this.addItem.bind(this),
            refreshDashboardData: this.refreshDashboardData.bind(this),
            updateDateFilter: this.updateDateFilter.bind(this),
            ksItemsCommonPropsForStructure: this.ksItemsCommonPropsForStructure.bind(this),
            updateFilter: this.updateFilter.bind(this),
            updateData: this.updateData.bind(this),
            silentUpdateData: this.silentUpdateData.bind(this),
        }
    }

    silentUpdateData(vals){
        Object.assign(this.state.dashboardData, vals)
    }

    updateData(vals){
        Object.assign(this.state.dashboardData, markRaw({ ...this.state.dashboardData, ...vals }))
    }

    ksItemsCommonPropsForStructure(){
        return {
            itemsBasicData: this.state.itemsBasicData,
            dashboardData: this.state.dashboardData,
            dateFilterConfig: this.state.dateFilterConfig,
            filtersConfig: this.state.filtersConfig,
            dnStore: this.dnStore,
        }
    }

    isDashboardManager(){
        return this.isDashboardManager
    }

    addItem(itemsDataToAdd){
        const useEffectActions = itemsDataToAdd.map(itemDataToAdd => ({ itemBasicData: itemDataToAdd, type: 'addGsItem' }))
        this.env.bus.trigger(this.KsItemsEventName, { useEffectActions })

        this.state.itemsBasicData.push(...itemsDataToAdd)
        this.DNGridStack.saveLayout(this.state.dashboardData.gs_layouts_info.defaultLayout)
    }

    updateItem(itemsDataToUpdate){
        const useEffectActions = itemsDataToUpdate.map(data => ({ itemBasicData: data, type: 'updateGsItem' }))
        this.env.bus.trigger(this.KsItemsEventName, { useEffectActions })

        const itemMap = new Map(itemsDataToUpdate.map(data => [data.id, data]))
        this.state.itemsBasicData = this.state.itemsBasicData.map(data => {
            const updatedData = itemMap.get(data.id);
            return updatedData ? { ...data, ...updatedData } : data;
        })
    }

    removeItem(itemDataToRemove){

        let index = this.state.itemsBasicData.findIndex( (itemData) => itemData.id === itemDataToRemove.id )

        if (index !== -1) {
            let node = this.DNGridStack.gridStack.engine.nodes.find((node) => node.el.id == itemDataToRemove.id)
            if(node){
                this.DNGridStack.gridStack.removeWidget(node.el)
            }

            this.state.itemsBasicData.splice(index, 1);
            // TODO: r&d other method other than compact, to only fill the space leaved , not change the layout for all items as compact does
            this.DNGridStack.gridStack.compact()
            this.DNGridStack.saveLayout(this.state.dashboardData.gs_layouts_info.defaultLayout)
        }
    }

    // TODO: this method is to update dashboard data without reload after change from settings
    refreshDashboardData(record){}

    updateDateFilter(config){
        //TODO: why date filters has be added in the context  while fecthing?? it creates unncessary confusion , it should be passed as params
        let updatedConfig = {
            dateSelection: config.dateSelection,
            startDate: config.startDate,
            endDate: config.endDate,
        }
        this.state.dateFilterConfig = updatedConfig
    }

    update_dashboard_mode(mode){
        this.ks_mode = mode;
    }

    updateFilter(models, domainData){
        sessionStorage.removeItem(sessionKeys.dashboardDomainData + this.state.dashboardData.id)
        this.state.filtersConfig = { domainData, lastUpdatedModels: models }

        setSessionStorage(sessionKeys.dashboardDomainData + this.state.dashboardData.id, this.state.filtersConfig, this.notification)
    }
}

registry.category("actions").add("ks_dashboard_ninja", KsDashboardNinja);
