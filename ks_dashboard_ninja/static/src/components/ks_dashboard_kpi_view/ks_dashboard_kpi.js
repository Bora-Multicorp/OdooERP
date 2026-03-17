
import { Component, useState, onWillUpdateProps, useEffect, onMounted, useRef, onWillUnmount } from "@odoo/owl";
import { globalfunction } from '@ks_dashboard_ninja/js/dn_utils';
import { formatFloat } from "@web/core/utils/numbers";
import { formatInteger } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { onAudioEnded, ks_get_gcd, calcDeviation, x_multiplier, format_x_currency, dnNumberFormatter, dnCommonGetters } from '@ks_dashboard_ninja/js/dn_utils';
import { isMobileOS } from "@web/core/browser/feature_detection";
import { KsItemButton } from '@ks_dashboard_ninja/components/chart_buttons/chart_buttons';
import { standardDashboardItemProps, standardDashboardItemDefaultProps } from '@ks_dashboard_ninja/js/dn_utils';
import { setupItemEventBus } from '@ks_dashboard_ninja/js/access_utils';
import { Chart } from "@ks_dashboard_ninja/components/dashboard_items/chart/chart";
import { deepEqual } from "@web/core/utils/objects";
import { useChildRef } from "@web/core/utils/hooks";
import { ExplanationViewer } from "@ks_dashboard_ninja/components/explanation_viewer/explanation_viewer";


export class DNKpi extends Chart{

    static props = {
        ...standardDashboardItemProps(),
    }
    static template = "ks_dashboard_ninja.kpi_view"
    static components = { KsItemButton, ExplanationViewer }

    setup(){
        super.setup()
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.aiAudioRef = useRef("aiAudioRef");

        this.state = useState({
            config: this.props.itemConfig ?? false
        })

        this.allowItemFetching = true
        setupItemEventBus(this.env.bus, this.props)

        onWillUpdateProps(nextProps => {
            let update = 0

            if(!deepEqual(this.props.dateFilterConfig, nextProps.dateFilterConfig))  update++;

            if(nextProps.filtersConfig.lastUpdatedModels?.includes(this.props.basicData.ks_model_name))  update++;
            if(nextProps.filtersConfig.lastUpdatedModels?.includes(this.props.basicData.ks_model_name_2))  update++;

            if(update){
                this.props.dnStore.delete(nextProps.itemId)

                if(this.props.visibleItemSet.has(this.props.itemId))
                    this.fetchOrUpdateItem(nextProps)
                else
                    this.allowItemFetching = true
            }

        })


        Object.keys(dnCommonGetters).forEach((methodName) => {
            Object.defineProperty(this, methodName, {
                get: () => dnCommonGetters[methodName](this.state.config, this.props.item_id)
            })
        })

    }

    async fetchOrUpdateItem(props){

        this.hideRefreshButton()

        let kwargs = { context: this.getContext(props) }
        let domain = this.getDomain(props)

        let config = await this.props.dnStore.getData(props.itemId, domain, kwargs)
        this.state.config = config

        if(this.props.isAIExplanation && this.allowItemFetching && !config.ks_ai_analysis){
            this.fetchExplanation.cb?.()
        }

        this.allowItemFetching = false
    }

    isFinite(value){
        return isFinite(value) ? value : 0
    }

    get kpiDisplayValues(){
        let { value1, value2 } = this.computeDataValue()
        let separator = this.computeSeparator()
        let {
            formattedDeviation: targetFormattedDeviation, direction: targetDirection, rawDeviation: targetRawDeviation
        } = this.computeTargetDeviation(value1)
        let { formattedDeviation: periodFormattedDeviation, direction: periodDirection } = this.computePeriodDeviation(value1)
        const { ks_model_name_2, ks_data_comparison, ks_standard_goal_value } = this.state.config

        return {
            formattedValue1: this.formatValue(value1), formattedValue2: separator ? this.formatValue(value2) : '',
            separator, tooltip: this.computeTooltip(value1, value2, separator), targetFormattedDeviation, targetDirection,
            targetRawDeviation, periodFormattedDeviation, periodDirection,
            maxProgressBarValue: ks_model_name_2 && ks_data_comparison === 'Percentage' ? ks_standard_goal_value : 100
        }
    }

    computeTooltip(value1, value2, separator){
        return separator ? `${value1} ${separator} ${value2}` : `${value1}`
    }

    chartInsightsProps(){
        return {
            itemConfig: JSON.parse(JSON.stringify(this.state.config)),
        }
    }

    computeSeparator() {
        const { ks_goal_enable, ks_target_view, ks_model_name_2, ks_data_comparison } = this.state.config;

        if ((ks_goal_enable && ks_target_view === 'Progress Bar') || (ks_model_name_2 && ks_data_comparison === 'None'))
            return ' / '
        if (ks_model_name_2 && ks_data_comparison === 'Ratio')    return ' : ';
        return '';
    }

    computeDataValue() {
        let {
            ks_goal_enable, ks_target_view, ks_model_name_2, ks_data_comparison, ks_record_count, ks_precision_digits,
            ks_record_count_2, ks_standard_goal_value, ks_multiplier, ks_multiplier_active, ks_data_format
        } = this.state.config;
        const isProgressBar = ks_goal_enable && ks_target_view === 'Progress Bar';
//        ks_standard_goal_value = dnNumberFormatter(ks_standard_goal_value, ks_data_format, ks_precision_digits)

        if(ks_multiplier_active)
            [ks_record_count, ks_record_count_2] = x_multiplier([ks_record_count, ks_record_count_2], ks_multiplier)

        if (!ks_model_name_2) {
            return { value1: ks_record_count, value2: isProgressBar ? ks_standard_goal_value : false };
        }

        switch(ks_data_comparison) {
            case "Sum":
                return { value1: ks_record_count + ks_record_count_2, value2: isProgressBar ? ks_standard_goal_value : false };
            case "Ratio": {
                const gcd = ks_get_gcd(Math.round(ks_record_count), Math.round(ks_record_count_2)) || 1;
                return { value1: ks_record_count / gcd, value2: ks_record_count_2 / gcd };
            }
            case "Percentage":
                return { value1: (ks_record_count / ks_record_count_2) * 100, value2: isProgressBar ? ks_standard_goal_value : false };
            case "None":
            default:
                return { value1: ks_record_count, value2: ks_record_count_2 };
        }
    }

    computeTargetDeviation(achievedValue){
        const { ks_goal_enable, ks_standard_goal_value, ks_target_view, ks_model_name_2 } = this.state.config;

        if( ks_goal_enable && (!ks_model_name_2 || ['Percentage', 'Sum'].includes(this.state.config.ks_data_comparison))){
            const deviationType = ks_target_view === 'Progress Bar' ? 'relative' : 'absolute'
            return calcDeviation(achievedValue, ks_standard_goal_value, deviationType)
        }
        return {}
    }

    //TODO: Context ???? dashboard manager , user thing ?? comment ks_kpi_data compute field ---- Name not prsent use model name?? USE KS_PRECISION_DIDIGTS FROM GLOBAL OBJ REMOVE FROM ITEM CONFIGS
    computePeriodDeviation(currentPeriodValue){
        let {
            ks_date_filter_selection, ks_kpi_previous_period_data, ks_previous_period, ks_model_name_2,
            ks_multiplier_active, ks_multiplier
        } = this.state.config;
        const ks_valid_date_selection = ['l_day', 't_week', 't_month', 't_quarter', 't_year'];
        const isPreviousPeriod = [ks_date_filter_selection, this.env.getContext?.().ksDateFilterSelection].some(sel => ks_valid_date_selection.includes(sel))

        if(!ks_previous_period || ks_model_name_2 || !isPreviousPeriod) return {}

        if(ks_multiplier_active)
            [ks_kpi_previous_period_data] = x_multiplier([ks_kpi_previous_period_data], ks_multiplier)

        return calcDeviation(currentPeriodValue, ks_kpi_previous_period_data, 'absolute')
    }

    formatValue(value){
        const {
            ks_model_name_2, ks_data_comparison, ks_data_format, ks_precision_digits, ks_multiplier_active, ks_multiplier
        } = this.state.config

        if (value === false || !isFinite(value)) return String(value || '');

        if(ks_model_name_2 && ks_data_comparison === 'Ratio')   return `${value}`

        if(ks_model_name_2 && ks_data_comparison === 'Percentage'){
            if(ks_multiplier_active)    value *= ks_multiplier
            return ks_data_format === 'exact' ?
                `${formatFloat(value, {digits: [0, ks_precision_digits]})} %` : `${Math.round(value)} %`
        }

        return format_x_currency(this.state.config, value)
    }

    onKpiClick() {
        if(this.env.inDialog)   return
        if(this.state.config.ks_data_calculation_type === 'query')   return
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

    ksPercentage(count_1, count_2, field, item_info, target_1, kpi_data) {
        item_info.target_progress_deviation = item_info['count']
        target_1 = target_1 > 100 ? 100 : target_1;
        item_info.target = target_1 + "%";
        item_info.pre_arrow = (target_1 - count) > 0 ? "down" : "up";
        item_info['ks_color'] = (target_1 - count) > 0 ? "red" : "green";
        item_info['target_enable'] = field.ks_goal_enable;
        item_info['ks_comparison'] = false;
        item_info.target_deviation = item_info.target > 100 ? 100 : item_info.target;
        return item_info
    }

};


