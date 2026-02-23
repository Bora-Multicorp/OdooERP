
import { pick } from "@web/core/utils/objects";

/*
*   Wrapper for GridStack - to be used as per DN
*/

// TODO: All the gridStack functionalities should be moved to this class from dashboard components
export class DNGridStack {

    constructor(orm){
        this.orm = orm
        this.itemsBasicData = new WeakMap() // to be used for storing items basic data

        const DEFAULT_CHART_CONFIG_CB = (config, id) => {
            return {
                x: config?.x ?? null, y: config?.y ?? null, w: config?.w ?? null, h: config?.h ?? null,
                autoPosition: !config, minW: 4, maxW: null, minH: 6, maxH: null, id
            }
        }

        const DEFAULT_CARD_CONFIG_CB = (config, id) => {
            return {
                x: config?.x ?? null, y: config?.y ?? null, w: config?.w ?? null, h: config?.h ?? null,
                autoPosition: !config, minW: 2, maxW: null, minH: 3, maxH: null, id
            }
        }

        this.defaultGSConfig = { x: null, y: null, w: null, h: null, autoPosition: true, minW: 3, maxW: null, minH: 3, maxH: null}

        this.gsConfigMap = {
            'ks_tile': DEFAULT_CARD_CONFIG_CB,
            'ks_bar_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_horizontalBar_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_line_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_area_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_pie_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_doughnut_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_polarArea_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_radialBar_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_scatter_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_list_view': DEFAULT_CHART_CONFIG_CB,
            'ks_radar_view': DEFAULT_CHART_CONFIG_CB,
            'ks_flower_view': DEFAULT_CHART_CONFIG_CB,
            'ks_kpi': DEFAULT_CARD_CONFIG_CB,
            'ks_to_do': DEFAULT_CHART_CONFIG_CB,
            'ks_map_view': DEFAULT_CHART_CONFIG_CB,
            'ks_funnel_chart': DEFAULT_CHART_CONFIG_CB,
            'ks_bullet_chart': DEFAULT_CHART_CONFIG_CB
        }
    }


    gsInit(rootEl, options){
        this.gridStack = GridStack.init(options, rootEl)
        this.rootEl = rootEl
        this.options = options
        return this.gridStack
    }

    changeGrid(grid) {
        const gridItemEls = this.gridStack.getGridItems()

        gridItemEls.forEach( (itemEl) => {
            const itemBasicData = this.itemsBasicData.get(itemEl)
            const config = this.getConfig(itemBasicData, grid)

            this.gridStack.update(itemEl, config)
        })
    }

    updateGridEl(el, grid, itemBasicData){
        const config = this.getConfig(itemBasicData, grid)
        this.gridStack.update(el, config)
    }

    // TODO: im mobile i guess the layout doesnt save
    async saveLayout(layout){
        let grid_stack_config = this.currentGsConfig()
        await this.orm.write('ks_dashboard_ninja.grid_stack_layouts', [layout.id], { grid_stack_config })
    }

    currentGsConfig(params=[]){

        const configParams = [...new Set(['x', 'y', 'w', 'h', ...params])]
        let nodes = this.gridStack.engine.nodes;
        let gridConfig = {}

        for( let node of nodes){
            if(node.id)     gridConfig[node.id] = pick(node, ...configParams)
        }
        return gridConfig;
    }

    getConfig(itemBasicData, grid){
        const id = itemBasicData.id
        const type = itemBasicData.ks_dashboard_item_type
        const config = this.gsConfigMap[type]?.(grid[id], id) ?? this.defaultGSConfig
        return config
    }

    setEditedLayout(layout){
        this.makeStatic()
        this.saveLayout(layout)
    }

    makeStatic(){
        this.gridStack.setStatic(true)
        this.gridStack.commit()
    }

    makeEditable(){
        this.gridStack.setStatic(false);
        this.gridStack.enable();
    }


    makeGsItem(element, grid, itemBasicData){

        this.itemsBasicData.set(element, itemBasicData)
        this.gridStack.makeWidget(element)
        let config = this.getConfig(itemBasicData, grid)
        this.gridStack.update(element, config)
    }

}