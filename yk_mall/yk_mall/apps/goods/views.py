from datetime import datetime

from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.filters import OrderingFilter
from drf_haystack.viewsets import HaystackViewSet
from rest_framework_extensions.cache.mixins import ListCacheResponseMixin
from rest_framework.viewsets import GenericViewSet
from . import serializers
from .models import SKU, GoodsCategory
from .serializers import SKUSerializer, SKUIndexSerializer, OrderGoodsSerializer
from orders.models import OrderGoods, OrderInfo
from . import constants


# GET /orders/user/
class UserOrdersView(ListModelMixin,GenericViewSet):
    # 添加认证,登录用户才可以访问
    permission_classes = [IsAuthenticated]
    # 指定序列化器类
    serializer_class = OrderGoodsSerializer

    # 重写list方法
    def list(self, request, *args, **kwargs):
        # 获取登录用户
        user = request.user
        # 查询订单数据,按创建时间进行降序排列
        order = OrderInfo.objects.filter(user_id=user.id).order_by("-create_time")

        # 复制粘贴源代码中的分页功能代码
        queryset = self.filter_queryset(order)
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            for ser in serializer.data:

                create_time = ser.get('create_time').split('+')[0]
                # 原因出现在这里 后面多了个+号，貌似和时区有关
                # create_time 2019-08-05T18:52:04.420354+08:00

                # '2018-08-06T10:00:00.000000' 

                date_ = datetime.strptime(create_time, "%Y-%m-%dT%H:%M:%S.%f")

                new_date = "%d-%d-%d  %.02d:%02d:%02d" % (date_.year,date_.month,date_.day,date_.hour,date_.minute,date_.second)
                ser['create_time']=new_date


            return self.get_paginated_response(serializer.data)

        # 创建序列化器类对象
        serializer = self.get_serializer(order, many=True)
        for ser in serializer.data:
            create_time = ser.get('create_time').split('+')[0]

            # '2018-08-06T10:00:00.000000' 

            date_ = datetime.strptime(create_time, "%Y-%m-%dT%H:%M:%S.%f")
            new_date = "%d-%d-%d  %.02d:%02d:%02d" % (
            date_.year, date_.month, date_.day, date_.hour, date_.minute, date_.second)
            ser['create_time'] = new_date

        data = {
            'count': len(order),
            'results': serializer.data
        }

        # 3.返回与用户相关的商品信息给前端
        return Response(data)




class SKUListView(ListAPIView):
    """
    sku列表数据
    """
    serializer_class = serializers.SKUSerializer
    filter_backends = (OrderingFilter,)
    ordering_fields = ('create_time', 'price', 'sales')

    def get_queryset(self):
        category_id = self.kwargs['category_id']
        print(category_id)
        s =  SKU.objects.filter(category_id=category_id,is_launched=True)
        return s


class SKUSearchViewSet(HaystackViewSet):
    """
    SKU搜索
    """
    index_models = [SKU]

    serializer_class = SKUIndexSerializer


class CategoryView(GenericAPIView):
    """
    类别
    """
    queryset = GoodsCategory.objects.all()

    def get(self, request, pk=None):
        ret = dict(
            cat1='',
            cat2='',
            cat3=''
        )
        category = self.get_object()
        if category.parent is None:
            # 当前类别为一级类别
            ret['cat1'] = serializers.ChannelSerializer(category.goodschannel_set.all()[0]).data
        elif category.goodscategory_set.count() == 0:
            # 当前类别为三级
            ret['cat3'] = serializers.CategorySerializer(category).data
            cat2 = category.parent
            ret['cat2'] = serializers.CategorySerializer(cat2).data
            ret['cat1'] = serializers.ChannelSerializer(cat2.parent.goodschannel_set.all()[0]).data
        else:
            # 当前类别为二级
            ret['cat2'] = serializers.CategorySerializer(category).data
            ret['cat1'] = serializers.ChannelSerializer(category.parent.goodschannel_set.all()[0]).data

        return Response(ret)


class HotSKUListView(ListCacheResponseMixin, ListAPIView):
    """
    热销商品, 使用缓存扩展
    """
    serializer_class = SKUSerializer
    pagination_class = None

    def get_queryset(self):
        category_id = self.kwargs['category_id']
        return SKU.objects.filter(category_id=category_id, is_launched=True).order_by('-sales')[0:constants.HOT_SKUS_COUNT_LIMIT]
