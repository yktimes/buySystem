import xadmin
from xadmin import views
from .models import Payment




class OrderGoodsAdmin(object):
    """订单信息管理类"""

    list_display = ['order', 'trade_id']
    search_fields = ['trade_id']
    list_filter = ['order']
    list_editable = ['order']
    show_detail_fields = ['order', 'trade_id']


xadmin.site.register(Payment,OrderGoodsAdmin)
