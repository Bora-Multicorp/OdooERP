
export class DNDashboardStore{

    constructor(orm){
        this.orm = orm
        this.data = {}
    }

    async getData(id, domain, kwargs){
        if(this.data[id]){
            return this.data[id]
        }

        let result = await this.fetchItem(id, domain, kwargs)

        this.data[id] = Promise.resolve(result)
        return this.data[id]


    }

    delete(id){
        delete this.data[id]
    }

    async fetchItem(id, domain, kwargs){
        const result = await this.orm.call('ks_dashboard_ninja.item' , 'get_item_config', [[id], domain], kwargs)
        return result
    }

}