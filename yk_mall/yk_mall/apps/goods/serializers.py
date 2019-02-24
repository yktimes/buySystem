from rest_framework import serializers
from .models import SKU

class SKUSerializer(serializers.ModelSerializer):
    """
    SKU序列化器
    """
    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'default_image_url', 'comments')

from drf_haystack.serializers import HaystackSerializer
from . search_indexes import SKUIndex
class SKUIndexSerializer(HaystackSerializer):
    """
    KU索引结果数据序列化器
    """

    object = SKUSerializer(read_only=True)


    class Meta:
        index_classes = [SKUIndex]
        fields = ('text','object')