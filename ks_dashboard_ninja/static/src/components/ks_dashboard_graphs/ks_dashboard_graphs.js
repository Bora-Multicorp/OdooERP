
import { Component, onWillStart, useState, useEffect, onMounted, onPatched, onWillUpdateProps, useRef, onWillUnmount, markup, reactive } from "@odoo/owl";
import { KsItemButton } from '@ks_dashboard_ninja/components/chart_buttons/chart_buttons';
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useBus, useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/core/utils/numbers";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { formatDate, formatDateTime, parseDateTime, parseDate } from "@web/core/l10n/dates";
import { renderToElement, renderToString } from "@web/core/utils/render";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { renderGraph, renderFunnelGraph, renderMapGraph } from "@ks_dashboard_ninja/js/chart_utils";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { standardDashboardItemProps, standardDashboardItemDefaultProps, onAudioEnded, convert_data_to_utc } from '@ks_dashboard_ninja/js/dn_utils';
import { setupItemEventBus, useChildCb } from '@ks_dashboard_ninja/js/access_utils';
import { ExplanationViewer } from "@ks_dashboard_ninja/components/explanation_viewer/explanation_viewer";
import { Chart } from "@ks_dashboard_ninja/components/dashboard_items/chart/chart";
import { deepCopy, deepEqual } from "@web/core/utils/objects";

export class DNGraph extends Chart{

    static template = "ks_dashboard_ninja.dn_graph_view"
    static components = { KsItemButton, Dropdown, DropdownItem, ExplanationViewer }
    static props = {
        ...standardDashboardItemProps(),
    }


    setup(){
        super.setup()
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.markup = markup;
        this.aiAudioRef = useRef("aiAudioRef");
        this.ks_list_view = useRef("ks_list_view");
        this.rootRef = useRef("rootRef");
        this.graphRef = useRef("graphRef");

        this.state = useState({
            config : false,
            actions : [],
            listViewConfig: {},
            type: 'graph',
        })

        this.listViewActionsConfig = { currentOffset: 0, listOrderConfig: false }

        this.chartConfig = reactive({
            chartData: false,
        }, this.renderChart.bind(this))

        this.root = false
        this.allowItemFetching = true
        this.activeChartActions = false

        onWillUpdateProps(nextProps => {
            let update = 0
            if(nextProps.isFormPreview){
                return
            }

            if(!deepEqual(this.props.dateFilterConfig, nextProps.dateFilterConfig))  update++

            if(nextProps.filtersConfig.lastUpdatedModels?.includes(this.props.basicData.ks_model_name))  update++

            if(update){
                this.props.dnStore.delete(nextProps.itemId)

                if(this.props.visibleItemSet.has(this.props.itemId))
                    this.fetchOrUpdateItem(nextProps)
                else
                    this.allowItemFetching = true
            }

        })

        setupItemEventBus(this.env.bus, this.props)

        useEffect(() => {
            if(this.props.itemConfig){
                this.setStateConfigs(this.props.itemConfig)
            }
        }, () => [])

        onWillUnmount(() => {
            this.root?.dispose?.()
        })
    }

    // TODO: Python changes needs to be done to make this component process more smooth and easy to understand

    parseConfigs(config){
        let listViewConfig
        let chartConfig

        if(!config) return config

        if(config.ks_dashboard_item_type === 'ks_list_view'){
            listViewConfig = typeof config.ks_list_view_data === 'string' ? JSON.parse(config.ks_list_view_data) : config.ks_list_view_data
            if(!this.props.itemConfig)    delete config.ks_list_view_data
        }
        else{
            chartConfig = config.ks_chart_data
            if(!this.props.itemConfig)    delete config.ks_chart_data
        }
        return { config, listViewConfig, chartConfig }
    }

    setStateConfigs(itemConfig){
        let { config, listViewConfig, chartConfig } = this.parseConfigs(itemConfig)

        if(listViewConfig){
            Object.assign(this.state, {
                listViewConfig, actions: [{ name: config.name, isMain: true }], type: 'list', config: config
            })
        }
        else{
            this.root.dispose?.()
            Object.assign(this.state, {
                actions: [{ name: config.name, isMain: true }], type: 'graph', config: config
            })
            this.chartConfig.chartData = { ...this.chartConfig.chartData, ...chartConfig }
        }

        if(this.props.isAIExplanation && this.allowItemFetching && !itemConfig.ks_ai_analysis){
            this.fetchExplanation.cb?.()
        }
    }

    get itemActions(){
        return {
            context: this.getContext(this.props),
            domain: this.getDomain(this.props)
        }
    }

    async fetchOrUpdateItem(props){
        this.root?.dispose?.()
        this.hideRefreshButton()
        this.activeChartActions = false

        let kwargs = { context: this.getContext(props) }
        let domain = this.getDomain(props)
        let itemConfig = await this.props.dnStore.getData(props.itemId, domain, kwargs)

        this.setStateConfigs(deepCopy(itemConfig))
        this.allowItemFetching = false
    }

    renderChart(){
        let chartType = this.state.config.ks_dashboard_item_type

        if(this.activeChartActions){
            chartType = this.chartConfig.chartData.ks_dashboard_item_type
        }

        if(chartType === 'ks_funnel_chart')
            this.root = renderFunnelGraph(this.root, this.graphRef.el, deepCopy(this.chartConfig.chartData),
                                    deepCopy(this.state.config), this.chartCanvasClick.bind(this), chartType)
        else if(chartType === 'ks_map_view')
            this.root = renderMapGraph(this.root, this.graphRef.el, deepCopy(this.chartConfig.chartData),
                                    deepCopy(this.state.config), this.chartCanvasClick.bind(this), chartType)
        else
            this.root = renderGraph(this.root, this.graphRef.el, deepCopy(this.chartConfig.chartData),
                                        deepCopy(this.state.config), this.chartCanvasClick.bind(this), chartType)
    }

    chartInsightsProps(){
        return {
            itemConfig: JSON.parse(JSON.stringify(this.state.config)),
        }
    }

    async onPageUpdate(direction) {
        if (this.isPageUpdating) return;

        this.isPageUpdating = true;
        const limit = this.state.config.ks_pagination_limit;
        const total = this.state.listViewConfig.total
        let offset = this.listViewActionsConfig.currentOffset + limit * direction

        if(offset >= total){
            offset = 0;
        } else if (offset < 0) {
            offset = total - (total % limit || limit);
        }

        this.listViewActionsConfig.currentOffset = offset
        await this.updateListViewData(offset, limit);
        this.isPageUpdating = false;
    }

    get totalPagesCount(){
        return Math.ceil(this.state.listViewConfig.total/this.state.config.ks_pagination_limit)
    }

    get currentPageCount(){
        return Math.floor(this.listViewActionsConfig.currentOffset/this.state.config.ks_pagination_limit) + 1
    }

    get end(){
        return Math.min(
            this.listViewActionsConfig.currentOffset + this.state.config.ks_pagination_limit,
            this.state.listViewConfig.total
        )
    }

    get start(){
        return this.listViewActionsConfig.currentOffset + 1
    }

    get getLayoutClasses(){
        let layouts = {
            layout_2: 'ks_list_view_layout_2',
            layout_3: 'ks_list_view_layout_3',
            layout_4: 'ks_list_view_layout_4',
        }
        return layouts[this.state.config.ks_list_view_layout]
    }


    async updateListViewData(offset = 0){

        if(offset > 0){
            this.activeChartActions = true
        }
        else{
            this.activeChartActions = false
        }

        let args = [[this.props.itemId], { offset }, this.getDomain(this.props)]
        let kwargs = { context: this.getContext(this.props)}
        let updatedListViewConfig = await this.orm.call('ks_dashboard_ninja.item', 'ks_get_next_offset', args, kwargs)
        this.state.listViewConfig = updatedListViewConfig.ks_list_view_data

    }

    async updateChartColor(color) {

        let config = await this.props.dnStore.data[this.props.itemId]

        if(!config.ks_chart_data)   return

        config.ks_chart_data.ks_chart_item_color = color
        this.state.config.ks_chart_item_color = color
        if(this.chartConfig.chartData.ks_chart_item_color != color){
            this.chartConfig.chartData.ks_chart_item_color = color
        }
    }

    calcActionDomain(ev){
        let activePoint = ev.target.dataItem?.dataContext;
        let domain = []
        let labels = this.chartConfig.chartData.labels
        let domains = this.chartConfig.chartData.domains
        if (activePoint) {
            let index;
            if (activePoint.category){
                index = labels.indexOf(activePoint.category)
            }
            else if (activePoint.stage){
                index = labels.indexOf(activePoint.stage)
            }
            domain = index >= 0 ? domains[index] : []
        }
        if (typeof domain === 'object' && domain !== null && !Array.isArray(domain)) {
            domain = domain[ev.target.dataItem.component._settings.name]
        }
        return domain
    }

    async chartCanvasClick(ev){

        // TODO: put here conditions when canvas should not  be clickable
        if(this.env.inDialog || this.state.config.ks_data_calculation_type === 'query') return;

        if(this.actionLoading) return;

        this.actionLoading = true
        let actionSequence = this.state.actions.at(-1)?.nextSequence ?? 0;
        let domain = this.calcActionDomain(ev)
        let args = [[this.props.itemId], domain, actionSequence]
        let groupBy = this.chartConfig.chartData.groupby

        if(
            await this.validateDomain(
                domain, this.state.config.action ? this.state.config.action.res_model : this.state.config.ks_model_name
            )
        ){
            this.actionLoading = false;
            return;
        }

        if(this.state.actions.length <= this.state.config.chart_actions_length){
            this.activeChartActions = true
            let config = await this.orm.call('ks_dashboard_ninja.item', 'ks_fetch_drill_down_data', args, {})
            config.hasOwnProperty('ks_chart_data') ? this.setActionChart(config) : this.setActionList(config)
            this.state.actions.push({ sequence: actionSequence, domain, name: config.ks_action_name, nextSequence: config.next_sequence})
        }
        else if(this.state.config.ks_show_records){
            this.callItemAction(domain, groupBy)
        }
        this.actionLoading = false
    }

    async validateDomain(domain, model){
        let isValid = await rpc("/web/domain/validate", { model, domain })

        if(!isValid){
            this.notification.add(_t("Invalid Domain"), { type: 'danger' });
            return true;
        }
        return false;
    }

    setActionChart(config){
        let chartConfig = config.ks_chart_data
        this.state.type = 'graph'
        this.chartConfig.chartData = { ...this.chartConfig.chartData, ...chartConfig }
    }

    setActionList(config){
        this.root.dispose?.()
        this.state.listViewConfig = config.ks_list_view_data
        this.state.type = 'list'
    }

    async drillUp(action) {
        if(action.isMain) {
            this.activeChartActions = false
            // TODO: is it required to delete ?
            this.props.dnStore.delete(this.props.itemId)
            this.fetchOrUpdateItem(this.props)
            return;
        }

        this.state.actions.splice(action.sequence + 2)
        let args = [[this.props.itemId], action.domain, action.sequence]
        let config = await this.orm.call('ks_dashboard_ninja.item', 'ks_fetch_drill_down_data', args)
        config.hasOwnProperty('ks_chart_data') ? this.setActionChart(config) : this.setActionList(config)
    }

    onColumnCellClick(column){
        if(column.store && this.state.actions.length <= 1){
            this.debouncedSortList?.(column)
        }
    }

    applyChartFilter(field_name, value){
        this.env.bus.trigger("APPLY: Dashboard Filter" ,{
            model_display_name: this.state.config.ks_model_display_name,
            model_name: this.state.config.ks_model_name,
            field_name,
            operator : '=',
            value
        })
    }

    async onRecordCellClick(recordData, fieldName){

        if(this.isCellClicked || this.props.isPreview)  return;

        this.isCellClicked = true

        if(this.state.config.ks_list_view_type !== 'ungrouped' && this.state.config.chart_actions_length){

            if(this.state.actions.length > this.state.config.chart_actions_length){
                this.isCellClicked = false
                return;
            }

            let actionSequence = this.state.actions.at(-1)?.nextSequence ?? 0;
            this.activeChartActions = true

            // TODO: check need for checking recordData.domain === 'string' ?? is it necessary ??
            let domain = typeof recordData.domain === 'string' ? JSON.parse(recordData.domain) : recordData.domain

            let args = [[this.props.itemId], domain, actionSequence]

            let config = await this.orm.call('ks_dashboard_ninja.item', 'ks_fetch_drill_down_data', args, {})
            config.hasOwnProperty('ks_chart_data') ? this.setActionChart(config) : this.setActionList(config)
            this.state.actions.push({ sequence: actionSequence, domain, name: config.ks_action_name, nextSequence: config.next_sequence})

            this.isCellClicked = false
            return;
        }

        this.isCellClicked = false

        if(['many2one', 'selection'].includes(this.state.listViewConfig.columns[fieldName].ttype)){
            this.applyChartFilter(fieldName, recordData.data[fieldName].tech_value ?? false)
        }
    }

    openRecord(record){

        let type = this.state.actions.length > 1 ? 'grouped' : this.state.config.ks_list_view_type
        let groupBy = this.state.listViewConfig.groupby

        let action = {
            name: _t(this.state.config.name),
            type: 'ir.actions.act_window',
            res_model: this.state.config.ks_model_name,
            domain: type === 'grouped' ? record.domain ?? [] : this.state.config.ks_domain || [],
            views: type === 'grouped' ? [[false, 'list'], [false, 'form']] : [[false, 'form']],
            view_mode: type === 'grouped' ? 'list' : 'form',
            view_type: type === 'grouped' ? 'list' : 'form',
            target: 'current',
            ...(type === 'ungrouped' ? { res_id: record.id } : {}),
            ...(type === 'grouped' ? { context: {'group_by': groupBy} } : {})
        }

        if(type === 'grouped' && ['relational_type', 'other'].includes(this.state.listViewConfig.list_view_type)){
            action['context']['search_default_' + groupBy] = record.groupById
        }

        this.actionService.doAction(action)
    }

    async callItemAction(domain = [], groupBy = false){
        let action;

        if (this.state.config.action) {
            action = Object.assign(this.state.config.action , { domain });
        }
        else {
            action = {
                name: _t(this.state.config.name),
                type: 'ir.actions.act_window',
                res_model: this.state.config.ks_model_name,
                domain: domain,
                context: { 'group_by': groupBy || false },
                views: [[false, 'list'], [false, 'form']],
                view_mode: 'list',
                target: 'current',
            }
        }
        this.actionService.doAction(action, {})
    }
};


