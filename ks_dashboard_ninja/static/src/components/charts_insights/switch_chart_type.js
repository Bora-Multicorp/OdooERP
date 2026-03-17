
import { Component, useState } from "@odoo/owl";


export class SwitchChartType extends Component {

    static template = "ks_dashboard_ninja.switch_chart_type"
    static props = {
        chartInsightActions: { type: Object },
        activeItemType: { type: String }
    }

    setup(){
        this.state = useState({
            itemType: this.props.activeItemType
        })

    }

    getItemTypes(){
        return ['ks_bar_chart', 'ks_area_chart', 'ks_pie_chart', 'ks_radialBar_chart', 'ks_funnel_chart']
    }

    switchItem(itemType){
        this.state.itemType = itemType
        this.props.chartInsightActions.changeItemType(itemType)
    }



}