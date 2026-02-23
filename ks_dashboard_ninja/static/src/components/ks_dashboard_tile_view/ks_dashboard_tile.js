/** @odoo-module **/
import { Component, useState ,useEffect,onWillUpdateProps,useRef, onMounted, onWillUnmount} from "@odoo/owl";
import { dnNumberFormatter, callItemAction, onAudioEnded, standardDashboardItemProps, standardDashboardItemDefaultProps,
            ksGetCurrency, formatStyle, dnCommonGetters } from '@ks_dashboard_ninja/js/dn_utils';

import { setupItemEventBus } from '@ks_dashboard_ninja/js/access_utils';
import { loadBundle } from "@web/core/assets";
import { useService, useBus } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { KsItemButton } from '@ks_dashboard_ninja/components/chart_buttons/chart_buttons';
import { hexToRGBA, darkenColor } from "@web/core/colors/colors";
import { session } from "@web/session";
import { ExplanationViewer } from "@ks_dashboard_ninja/components/explanation_viewer/explanation_viewer";
import { deepEqual } from "@web/core/utils/objects";
import { Chart } from "@ks_dashboard_ninja/components/dashboard_items/chart/chart";


export class DNTile extends Chart{

    static template = "tile_view"
    static components = { KsItemButton, ExplanationViewer }
    static  props = {
        ...standardDashboardItemProps(),
    }

    setup(){
        super.setup()
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.tileRootRef = useRef('tileRootRef');

        this.allowItemFetching = true


        this.state = useState({
            config : this.props.itemConfig ?? false
        })

        Object.keys(dnCommonGetters).forEach((methodName) => {
            Object.defineProperty(this, methodName, {
                get: () => dnCommonGetters[methodName](this.state.config)
            })
        })

        onWillUpdateProps(nextProps => {
            let update = 0

            if(!deepEqual(this.props.dateFilterConfig, nextProps.dateFilterConfig))  update++;

            if(nextProps.filtersConfig.lastUpdatedModels?.includes(this.props.basicData.ks_model_name))  update++;

            if(update){
                this.props.dnStore.delete(nextProps.itemId)

                if(this.props.visibleItemSet.has(this.props.itemId))
                    this.fetchOrUpdateItem(nextProps)
                else
                    this.allowItemFetching = true
            }

        })

        setupItemEventBus(this.env.bus, this.props)


        useEffect(()=>{
        }, () => [])

    }

    chartInsightsProps(){
        return {
            itemConfig: JSON.parse(JSON.stringify(this.state.config)),
        }
    }

    async fetchOrUpdateItem(props){
        this.hideRefreshButton()

        let kwargs = { context: this.getContext(props) }
        let domain = this.getDomain(props)
        let config = await this.props.dnStore.getData(props.itemId, domain, kwargs)
        this.state.config = config;

        if(this.props.isAIExplanation && this.allowItemFetching && !config.ks_ai_analysis){
            this.fetchExplanation.cb()
        }

        this.allowItemFetching = false
    }

    get displayDataValue(){
        let config = this.state.config
        let currency = ksGetCurrency(config.ks_unit, config.ks_unit_selection, config.ks_currency_id, config.ks_chart_unit)
        if(currency.position === 'after')
            return `${this.format_x_multiplier(this.state.config.ks_record_count)}  ${currency.symbol}`
        else
            return `${currency.symbol}  ${this.format_x_multiplier(this.state.config.ks_record_count)}`
    }

    format_x_multiplier(num){
        if(this.state.config.ks_multiplier_active){
            num = num * this.state.config.ks_multiplier
        }
        return dnNumberFormatter(num, this.state.config.ks_data_format, this.state.config.ks_precision_digits)
    }

    showRefreshBtn(){
        this.refreshRef.el.disabled();
    }

    onTileClick(){
        if(this.env.inDialog)   return
        if(!this.state.config.ks_model_name)   return

        let action = {
            name: _t(this.state.config.name),
            type: 'ir.actions.act_window',
            res_model: this.state.config.ks_model_name,
            domain: this.state.config.ks_domain || "[]",
            views: [[false, 'list'], [false, 'form']],
            view_mode: 'list',
            target: 'current',
        }

        if(this.state.config.action){
            this.state.config.action.domain = this.state.config.ks_domain || []
        }

        this.actionService.doAction(this.state.config.action || action)
    }

};



