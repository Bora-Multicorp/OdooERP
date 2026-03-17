/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
const { Component, useEffect, useRef, useState, onMounted } = owl;
import { renderToElement, renderToString } from "@web/core/utils/render";
import { ksrendermapview } from "@ks_dashboard_ninja/js/chart_utils";
import { renderMapGraph } from "@ks_dashboard_ninja/js/chart_utils";
import { useRecordObserver } from "@web/model/relational_model/utils";


export class KsMapPreview extends Component {
    setup() {
        var self =this;
        this.root = false;
        this.orm = useService("orm");
        this.mapContainerRef = useRef("mapContainer");
        useEffect(() =>{
            this.root.dispose?.()
            this._Ks_render()
        })

        useRecordObserver((record) => {
        // read value of the all the fields to observe its changes
            const makeWidgetObservable = { ...record.data }
            if(makeWidgetObservable){
                this.root?.dispose?.()
            }
            if(this.mapContainerRef.el){
                this._Ks_render()
            }

        })

    }

    _Ks_render() {

        var self = this;
        var rec = this.props.record.data;
        if ($(self.mapContainerRef.el).find("div.graph_text").length){
            $(self.mapContainerRef.el).find("div.graph_text").remove();
        }
        if (rec.ks_dashboard_item_type === 'ks_map_view'){
            if(rec.ks_data_calculation_type !== "query"){
                if (rec.ks_model_id) {
                    if (rec.ks_chart_groupby_type == 'date_type' && !rec.ks_chart_date_groupby) {
                        return  $(self.mapContainerRef.el).append($("<div class='graph_text'>").text("Select Group by date to create chart based on date groupby"));
                    } else if (rec.ks_chart_data_count_type === "count" && !rec.ks_chart_relation_groupby) {
                        $(self.mapContainerRef.el).append($("<div class='graph_text'>").text("Select Group By to create chart view"));
                    } else if (rec.ks_chart_data_count_type !== "count" && (rec.ks_chart_measure_field.count === 0 || !rec.ks_chart_relation_groupby)) {
                        $(self.mapContainerRef.el).append($("<div class='graph_text'>").text("Select Measure and Group By to create chart view"));
                    } else if (!rec.ks_chart_data_count_type) {
                        $(self.mapContainerRef.el).append($("<div class='graph_text'>").text("Select Chart Data Count Type"));
                    } else {
                        this.root = renderMapGraph(this.root, this.mapContainerRef.el, JSON.parse(this.props.record.data.ks_chart_data),
                            this.props.record.data, () => {})
                    }
                } else {
                    $(self.mapContainerRef.el).append($("<div class='graph_text'>").text("Select a Model first."));
                }
            }else if(rec.ks_data_calculation_type === "query" && rec.ks_query_result) {
                if(rec.ks_xlabels && rec.ks_ylabels){
                    this.root = renderMapGraph(this.root, this.mapContainerRef.el, JSON.parse(this.props.record.data.ks_chart_data),
                            this.props.record.data, () => {})
                } else {
                    $(self.mapContainerRef.el).append($("<div class='graph_text'>").text("Please choose the X-labels and Y-labels"));
                }
            }else {
                    $(self.mapContainerRef.el).append($("<div class='graph_text'>").text("Please run the appropriate Query"));
            }
        }

    }

    async _fetchRecordsPartner(data) {
        let domain = [];
        if (data && data['ks_partners_map']) {
            domain = [['id', 'in', JSON.parse(data['ks_partners_map'])]]
        }
        const fields = ["partner_latitude", "partner_longitude", "name"];
        const records = await this.orm.searchRead("res.partner", domain, fields);
        return records
    }

}

KsMapPreview.template = "KsMapPreview";

export const ks_map_preview_field = {
    component:KsMapPreview,
    supportedTypes : ["char"]
};

registry.category("fields").add("ks_dashboard_map_preview", ks_map_preview_field);