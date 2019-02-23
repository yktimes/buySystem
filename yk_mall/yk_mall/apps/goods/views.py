from django.shortcuts import render
from rest_framework.generics import ListAPIView
# Create your views here.
from rest_framework.filters import OrderingFilter
from . import serializers
from .models import SKU

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
        print(s)
        return s