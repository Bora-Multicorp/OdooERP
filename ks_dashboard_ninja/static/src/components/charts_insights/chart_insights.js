/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { Component, useState, useRef, useChildSubEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { SwitchChartType } from '@ks_dashboard_ninja/components/charts_insights/switch_chart_type';
import { ks_render_graphs, ksrenderfunnelchart } from "@ks_dashboard_ninja/js/chart_utils";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { deepEqual } from "@web/core/utils/objects";

export class ChartInsights extends Component {

    static components = { Dialog, SwitchChartType }
    static template = "ks_dashboard_ninja.chart_insights";
    static props = {
        itemComponentInfo: { type: Object },
        onSave: { type: Function, optional: true },
        close: { type: Function },
    }

    static defaultProps = {
        onSave: () => {}
    }
    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");

        this.state = useState({
            itemComponentInfo: this.props.itemComponentInfo,
            renderCount: 0
        })

        this.itemFieldsChanges = {}
    }

    get featureVisibility(){
        let charts = ['ks_bar_chart', 'ks_horizontalBar_chart', 'ks_line_chart', 'ks_area_chart', 'ks_pie_chart',
                      'ks_doughnut_chart', 'ks_polarArea_chart', 'ks_radialBar_chart', 'ks_scatter_chart', 'ks_funnel_chart',
                      'ks_bullet_chart', 'ks_flower_view', 'ks_radar_view']
        return {
            'switch-chart-type': charts.includes(this.state.itemComponentInfo.props.itemConfig.ks_dashboard_item_type)
        }
    }

    get chartInsightActions(){
        return {
            changeItemType: this.changeItemType.bind(this),
        }
    }
    async changeItemType(itemType) {
        this.state.itemComponentInfo.props.itemConfig.ks_chart_data.ks_dashboard_item_type = itemType
        this.state.itemComponentInfo.props.itemConfig.ks_dashboard_item_type = itemType
        this.state.renderCount++

        this.itemFieldsChanges.ks_dashboard_item_type = itemType
    }

    async onSave(){
        if(Object.keys(this.itemFieldsChanges).length === 0){
            this.props.close()
            return;
        }

        let itemId = this.state.itemComponentInfo.props.itemConfig.id

        // TODO: check for  funnel charts fields
        await this.orm.write('ks_dashboard_ninja.item', [itemId], this.itemFieldsChanges)
        this.props.onSave()
        this.props.close()
    }

}





