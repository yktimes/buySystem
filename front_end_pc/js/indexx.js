var vm = new Vue({
    el: '#app',

    data: {
        host,
        username: sessionStorage.username || localStorage.username,
        user_id: sessionStorage.user_id || localStorage.user_id,
        token: sessionStorage.token || localStorage.token,
        cart_total_count: 0, // 购物车总数量
        cart: [], // 购物车数据,
        sid:[],
        categories : {


        },
        contents : {
             index_1f_logo:{
                "image":""
             },
             index_2f_logo:{

             },
            index_3f_logo:{

             },
            index_lbt:{

            }

        },
        f1_tab: 1, // 1F 标签页控制
        f2_tab: 1, // 2F 标签页控制
        f3_tab: 1, // 3F 标签页控制
    },
    created: function () {
// `this` 指向 vm 实例

},
    mounted: function(){
        this.get_cart();
this.get_index()
    },
    methods: {
        // 退出
        logout: function(){
            sessionStorage.clear();
            localStorage.clear();
            location.href = '/login.html';
        },
        // 获取购物车数据
        get_cart: function(){
            axios.get(this.host+'/cart/', {
                    headers: {
                        'Authorization': 'JWT ' + this.token
                    },
                    responseType: 'json',
                    withCredentials: true
                })
                .then(response => {
                    this.cart = response.data;
                    this.cart_total_count = 0;
                    for(var i=0;i<this.cart.length;i++){
                        if (this.cart[i].name.length>25){
                            this.cart[i].name = this.cart[i].name.substring(0, 25) + '...';
                        }
                        this.cart_total_count += this.cart[i].count;

                    }
                })
                .catch(error => {
                    console.log(error.response.data);
                })
        },


          get_index: function(){
            axios.get(this.host+'/index/', {

                    responseType: 'json',
                    withCredentials: true
                })
                .then(response => {
                    this.categories = response.data.categories;
                    this.contents = response.data.contents;
                    this.sid=response.data.contents['index_lbt']
                    console.log( this.sid)

                })
                .catch(error => {
                    console.log(error.response.data);
                })
        }
    }
});