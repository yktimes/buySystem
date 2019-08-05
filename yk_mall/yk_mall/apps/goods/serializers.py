from rest_framework import serializers
from .models import SKU
from orders.models import OrderGoods, OrderInfo
from drf_haystack.serializers import HaystackSerializer
from . search_indexes import SKUIndex

class SKUSerializer(serializers.ModelSerializer):
    """
    SKU序列化器
    """
    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'default_image_url', 'comments')


class SKUIndexSerializer(HaystackSerializer):
    """
    KU索引结果数据序列化器
    """

    object = SKUSerializer(read_only=True)


    class Meta:
        index_classes = [SKUIndex]
        fields = ('text','object')


# 用来序列化和订单有关的商品信息
class OrderSkuSerializer(serializers.ModelSerializer):

    class Meta:
        model = SKU
        fields = ('default_image_url','name')


#用来序列化订单商品信息
class GoodsInfoSerializer(serializers.ModelSerializer):
    sku = OrderSkuSerializer()
    count = serializers.IntegerField(label='下单数量',read_only=True)
    price = serializers.DecimalField(max_digits=10,decimal_places=2,read_only=True)

    class Meta:
        model = OrderGoods
        fields = ('count','sku','price')



class OrderGoodsSerializer(serializers.ModelSerializer):
    '''订单基本信息序列化器类'''
    skus = GoodsInfoSerializer(many=True)

    class Meta:
        model = OrderInfo
        fields = ('create_time','order_id','total_amount','pay_method','status','skus','freight')