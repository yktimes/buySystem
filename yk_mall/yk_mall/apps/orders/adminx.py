import xadmin
from xadmin import views
from .models import OrderInfo,OrderGoods



class OrderInfoAdmin(object):
    """订单信息管理类"""
    # model_icon = 'fa fa-gift'
    list_display = ['order_id', 'user', 'address', 'total_amount', 'pay_method', 'status','freight']
    search_fields = ['order_id','status']
    list_filter = ['status','user']
    list_editable = ['status', 'freight']
    show_detail_fields = ['order_id']
    # list_export = ['xls', 'csv', 'xml']
    readonly_fields = ['pay_method']

    data_charts = {
        "order_amount": {'title': '订单金额', "x-field": "create_time", "y-field": ('total_amount',),
                         "order": ('create_time',)},
        "order_count": {'title': '订单量', "x-field": "create_time", "y-field": ('total_count',),
                        "order": ('create_time',)},
    }

class OrderGoodsAdmin(object):
    """订单信息管理类"""

    list_display = ['order', 'sku', 'count', 'price','score']
    search_fields = ['score']
    list_filter = ['score']
    list_editable = ['price', 'count','score']
    show_detail_fields = ['order','score']


xadmin.site.register(OrderInfo,OrderInfoAdmin)
xadmin.site.register(OrderGoods,OrderGoodsAdmin)