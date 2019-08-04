import base64
import pickle

from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from .serialziers import  CartSerializer,CartSKUSerializer,CartDeleteSerializer,CartSelectAllSerializer
from . import constants



from goods.models import SKU


# /cart/selection/
class CartSelectAllView(APIView):
    def perform_authentication(self, request):
        """让当前视图跳过DRF认证过程"""
        pass

    def put(self, request):
        """
        购物车全选和全不选:
        1. 接收参数selected并进行校验(必传)
        2. 获取user并进行处理
        3. 设置用户购物车记录勾选状态
            3.1 如果用户已登录，设置redis购物车记录勾选状态
            3.2 如果用户未登录，设置cookie购物车记录勾选状态
        4. 返回应答
        """
        # 1. 接收参数selected并进行校验(必传)
        serializer = CartSelectAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取参数
        selected = serializer.validated_data['selected']

        # 2. 获取user并进行处理
        try:
            user = request.user
        except Exception as e:
            user = None

        # 3. 设置用户购物车记录勾选状态
        if user is not None and user.is_authenticated:
            # 3.1 如果用户已登录，设置redis购物车记录勾选状态
            # 获取redis链接
            redis_conn = get_redis_connection('cart')

            # 获取redis中用户购物车中添加的商品id hash
            cart_key = 'cart_%s' % user.id
            # hkeys(key): 返回hash中所有属性
            # [b'<sku_id>', b'<sku_id>', ...]
            sku_ids = redis_conn.hkeys(cart_key)  # list

            # 设置redis用户购物车记录勾选状态 set
            cart_selected_key = 'cart_selected_%s' % user.id
            if selected:
                # 全选
                # sadd(key, *members)
                redis_conn.sadd(cart_selected_key, *sku_ids)
            else:
                # 全不选
                # srem(key, *members)
                redis_conn.srem(cart_selected_key, *sku_ids)
            return Response({'message': 'OK'})
        else:
            # 3.2 如果用户未登录，设置cookie购物车记录勾选状态
            response = Response({'message': 'OK'})
            # 尝试从cookie中获取原始的购物车数据
            cookie_cart = request.COOKIES.get('cart')  # None

            if cookie_cart is None:
                return response

            # 解析cookie中购物车数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = pickle.loads(base64.b64decode(cookie_cart))  # {}

            if not cart_dict:
                return response

            # 设置cookie购物车记录勾选状态
            for sku_id in cart_dict:
                cart_dict[sku_id]['selected'] = selected

            # 设置cookie
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_data, expires=constants.CART_COOKIE_EXPIRES)

            # 4. 返回应答
            return response


from collections import OrderedDict
from django.conf import settings
from django.template import loader
import os
import time

from goods.models import GoodsChannel
from contents.models import ContentCategory
class CartView(APIView):
    """
    购物车
    """
    def perform_authentication(self, request):
        """
        重写父类的用户验证方法，不在进入视图前就检查JWT
        让当前视图跳过DRF认证过程
        """
        pass

    def delete(self, request):
        """
        购物车记录删除:
        1. 获取商品sku_id并进行校验(必传，sku_id对应的商品是否存在)
        2. 获取user并处理
        3. 删除用户的购物车记录
            3.1 如果用户已登录，删除redis中的购物车记录
            3.2 如果用户未登录，删除cookie中的购物车记录
        4. 返回应答
        """
        # 1. 获取商品sku_id并进行校验(必传，sku_id对应的商品是否存在)
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        sku_id = serializer.validated_data['sku_id']

        # 2. 获取user并处理
        try:
            user = request.user
        except Exception as e:
            user = None

        # 3. 删除用户的购物车记录
        if user is not None and user.is_authenticated:
            # 3.1 如果用户已登录，删除redis中的购物车记录
            # 获取redis链接
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()

            # 从redis中删除用户购物车对应的商品的id和数量count hash
            cart_key = 'cart_%s' % user.id
            # hdel(key, *fields): 删除hash中对应的属性和值，有则删除，无则忽略
            pl.hdel(cart_key, sku_id)

            # 从redis中删除用户购物车对应商品的勾选状态 set
            cart_selected_key = 'cart_selected_%s' % user.id
            # srem(key, *members): 从set中移除元素，如果元素不存在，直接忽略
            pl.srem(cart_selected_key, sku_id)

            pl.execute()

            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # 3.2 如果用户未登录，删除cookie中的购物车记录
            response = Response(status=status.HTTP_204_NO_CONTENT)
            # 尝试从cookie中获取原始的购物车数据
            cookie_cart = request.COOKIES.get('cart')  # None

            if cookie_cart is None:
                return response

            # 解析cookie中购物车数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = pickle.loads(base64.b64decode(cookie_cart))  # {}

            if not cart_dict:
                return response

            if sku_id in cart_dict:
                del cart_dict[sku_id]

                # 重新设置cookie
                # 设置cookie
                cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
                response.set_cookie('cart', cart_data, expires=constants.CART_COOKIE_EXPIRES)

            # 4. 返回应答
            return response

    def put(self, request):
        """
        购物车记录修改:
        1. 获取参数并进行校验(参数完整性，sku_id商品是否存在，count是否大于库存)
        2. 获取user并处理
        3. 修改用户的购物车记录
            3.1 如果用户已登录，修改redis中的购物车记录
            3.2 如果用户未登录，修改cookie中的购物车记录
        4. 返回应答
        """
        # 1. 获取参数并进行校验(参数完整性，sku_id商品是否存在，count是否大于库存)
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取参数
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']

        # 2. 获取user并处理
        try:
            user = request.user
        except Exception as e:
            user = None

        # 3. 修改用户的购物车记录
        if user is not None and user.is_authenticated:
            # 3.1 如果用户已登录，修改redis中的购物车记录
            # 获取redis链接
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()

            # 修改redis用户购物车中商品id和数量count hash
            cart_key = 'cart_%s' % user.id
            # hset(key, field, value): 将hash中指定属性field的值设置为value
            pl.hset(cart_key, sku_id, count)

            # 修改redis用户购物车中商品的勾选状态 set
            cart_selected_key = 'cart_selected_%s' % user.id

            if selected:
                # 勾选
                # sadd(key, *members)
                pl.sadd(cart_selected_key, sku_id)
            else:
                # 不勾选
                # srem(key, *members): 从set中移除元素，如果元素不存在，直接忽略
                pl.srem(cart_selected_key, sku_id)

            pl.execute()
            return Response(serializer.data)
        else:
            # 3.2 如果用户未登录，修改cookie中的购物车记录
            response = Response(serializer.data)
            # 尝试从cookie中获取原始的购物车数据
            cookie_cart = request.COOKIES.get('cart')  # None

            if cookie_cart is None:
                return response

            # 解析cookie中购物车数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = pickle.loads(base64.b64decode(cookie_cart))  # {}

            if not cart_dict:
                return response

            # 修改用户购物车对应商品的数量和勾选状态
            if sku_id in cart_dict:
                cart_dict[sku_id] = {
                    'count': count,
                    'selected': selected
                }

                # 设置cookie
                cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
                response.set_cookie('cart', cart_data, expires=constants.CART_COOKIE_EXPIRES)

            # 4. 返回应答
            return response


    def get(self, request):

        """
        购物车记录获取:
        1. 获取user
        2. 获取用户的购物车记录
            2.1 如果用户已登录，从redis中获取用户的购物车记录
            2.2 如果用户未登录，从cookie中获取用户的购物车记录
        3. 根据用户购物车中商品的id查询对应商品的信息
        4. 把商品数据序列化并返回
        """
        # 1. 获取user
        try:
            user = request.user
        except Exception as e:
            user = None

        # 2. 获取用户的购物车记录
        if user is not None and user.is_authenticated:
            # 2.1 如果用户已登录，从redis中获取用户的购物车记录
            # 获取redis链接
            redis_conn = get_redis_connection('cart')

            # 从redis中获取用户购物车中添加的商品sku_id和对应数量count hash
            cart_key = 'cart_%s' % user.id
            # hgetall(key): 返回hash中所有属性和值
            # {
            #     b'<sku_id>': b'<count>',
            #     b'<sku_id>': b'<count>',
            #     ...
            # }
            cart_redis = redis_conn.hgetall(cart_key)  # dict

            # 从redis中获取用户购物车勾选商品sku_id set
            cart_selected_key = 'cart_selected_%s' % user.id
            # smembers(key): 获取set中所有元素
            # (b'<sku_id>', b'<sku_id>', ...)
            cart_selected_redis = redis_conn.smembers(cart_selected_key)  # set

            # 组织数据
            # {
            #     '<sku_id>': {
            #         'count': '<count>',
            #         'selected': '<selected>'
            #     },
            #     ...
            # }
            cart_dict = {}
            for sku_id, count in cart_redis.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected_redis
                }
        else:
            # 2.2 如果用户未登录，从cookie中获取用户的购物车记录
            # 尝试从cookie中获取原始的购物车数据
            cookie_cart = request.COOKIES.get('cart')  # None

            if cookie_cart:
                # 解析cookie中购物车数据
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}

        # 3. 根据用户购物车中商品的id查询对应商品的信息
        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)

        for sku in skus:
            # 给sku对象增加属性count和selected
            # 分别保存用户购物车中添加的该商品的数量和勾选状态
            sku.count = cart_dict[sku.id]['count']
            sku.selected = cart_dict[sku.id]['selected']

        # 4. 把商品数据序列化并返回
        serializer = CartSKUSerializer(skus, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        购物车记录添加:
        1. 接收参数并进行参数校验(参数完整性，sku_id商品是否存在，count是否大于库存)
        2. 保存添加的购物车记录
            2.1 如果用户已登录，在redis中保存用户的购物车记录
            2.2 如果用户未登录，在cookie中保存用户的购物车记录
        3. 返回应答
        """
        # 1. 接收参数并进行参数校验(参数完整性，sku_id商品是否存在，count是否大于库)

        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 获取参数
        sku_id = serializer.validated_data['sku_id']
        count = serializer.validated_data['count']
        selected = serializer.validated_data['selected']

        # 获取user
        try:
            user = request.user
        except Exception as e:
            user = None

        # 2. 保存添加的购物车记录


        if user  and user.is_authenticated:
            # 2.1 如果用户已登录，在redis中保存用户的购物车记录
            # 获取redis链接
            redis_conn = get_redis_connection('cart')

            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()

            # 在redis中存储用户添加的商品id和对应数量 hash
            cart_key = 'cart_%s' % user.id

            # 如果用户的购物车记录中已经添加过该商品，数量需要进行累加
            # 如果用户的购物车记录中没有添加过该商品，设置一个新的属性和值
            # hincrby(key, field, value): 给hash中field属性值累加一个value，如果field不存在，新建一个属性和值
            pl.hincrby(cart_key, sku_id, count)

            # 在redis中存储用户购物车记录勾选状态 set
            cart_selected_key = 'cart_selected_%s' % user.id

            if selected:
                # 勾选
                # sadd(key, *values): 向set中添加元素，不需要关注是否重复，set中元素唯一
                pl.sadd(cart_selected_key, sku_id)

            pl.execute()

            # 返回应答
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            # 2.2 如果用户未登录，在cookie中保存用户的购物车记录
            # 尝试从cookie中获取原始的购物车数据
            cookie_cart = request.COOKIES.get('cart')  # None

            if cookie_cart:
                # 解析cookie中购物车数据
                cart_dict = pickle.loads(base64.b64decode(cookie_cart))
            else:
                cart_dict = {}

            # 保存用户购物车添加数据
            if sku_id in cart_dict:
                # 数量进行累加
                count += cart_dict[sku_id]['count']

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 设置购物车cookie数据
            response = Response(serializer.data, status=status.HTTP_201_CREATED)
            # response.set_cookie(key, value, expires)
            cart_data = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('cart', cart_data, expires=constants.CART_COOKIE_EXPIRES)
            return response
