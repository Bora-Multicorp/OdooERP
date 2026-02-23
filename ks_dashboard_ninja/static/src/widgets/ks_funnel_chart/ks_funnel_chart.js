/** @odoo-module */

import { registry } from "@web/core/registry";
import { CharField } from "@web/views/fields/char/char_field";
const { Component, useEffect, useRef, useState } = owl;
import { renderToElement, renderToString } from "@web/core/utils/render";
import { renderGraph, renderFunnelGraph, renderMapGraph } from "@ks_dashboard_ninja/js/chart_utils";
import { useRecordObserver } from "@web/model/relational_model/utils";

export class ks_funnel_chart extends Component{
    setup(){
        this.root = false;
        this.funnelRef = useRef("funnel");
        useEffect(() =>{
            if(this.root){
                this.root.dispose?.()
            }
             this._Ks_render()
        })
        useRecordObserver((record) => {
            // read value of the all the fields to observe its changes
            const makeWidgetObservable = { ...record.data }
            if(makeWidgetObservable){
                this.root?.dispose?.()
            }
            if(this.funnelRef.el){
                this._Ks_render()
            }
        })
    }

    _Ks_render(){
        var self = this;
        var rec = this.props.record.data;
        var rec = this.props.record.data;
        if ($(self.funnelRef.el).find("div.graph_text").length){
            $(self.funnelRef.el).find("div.graph_text").remove();
        }
        if (rec.ks_dashboard_item_type === 'ks_funnel_chart'){
            if(rec.ks_data_calculation_type !== "query"){
                if (rec.ks_model_id) {
                    if (rec.ks_chart_groupby_type == 'date_type' && !rec.ks_chart_date_groupby) {
                        return  $(self.funnelRef.el).append($("<div class='graph_text'>").text("Select Group by date to create chart based on date groupby"));
                    } else if (rec.ks_chart_data_count_type === "count" && !rec.ks_chart_relation_groupby) {
                        $(self.funnelRef.el).append($("<div class='graph_text'>").text("Select Group By to create chart view"));
                    } else if (rec.ks_chart_data_count_type !== "count" && (rec.ks_chart_measure_field.count === 0 || !rec.ks_chart_relation_groupby)) {
                        $(self.funnelRef.el).append($("<div class='graph_text'>").text("Select Measure and Group By to create chart view"));
                    } else if (!rec.ks_chart_data_count_type) {
                        $(self.funnelRef.el).append($("<div class='graph_text'>").text("Select Chart Data Count Type"));
                    } else {
                        this.root = renderFunnelGraph(this.root, this.funnelRef.el, JSON.parse(this.props.record.data.ks_chart_data),
                            this.props.record.data, () => {})
//                        ksrenderfunnelchart.bind(this)($(this.funnelRef.el), rec, 'preview');
                    }
                } else {
                    $(self.funnelRef.el).append($("<div class='graph_text'>").text("Select a Model first."));
                }
            }else if(rec.ks_data_calculation_type === "query" && rec.ks_query_result) {
                if(rec.ks_xlabels && rec.ks_ylabels){
                    this.root = renderFunnelGraph(this.root, this.funnelRef.el, JSON.parse(this.props.record.data.ks_chart_data),
                                this.props.record.data, () => {})

                } else {
                    $(self.funnelRef.el).append($("<div class='graph_text'>").text("Please choose the X-labels and Y-labels"));
                }
            }else {
                    $(self.funnelRef.el).append($("<div class='graph_text'>").text("Please run the appropriate Query"));

            }

        }
    }

}

ks_funnel_chart.template = "Ksfunnelchart";
export const ks_funnel_chart_field = {
    component: ks_funnel_chart,
    supportedTypes : ["char"]
}
registry.category("fields").add("ks_funnel_chart", ks_funnel_chart_field);