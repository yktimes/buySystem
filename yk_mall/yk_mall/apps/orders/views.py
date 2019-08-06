from decimal import Decimal
from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, CreateAPIView
from rest_framework.permissions import IsAuthenticated

from goods.models import SKU
from .serializers import OrderSettlementSerializer,SaveOrderSerializer, OrderCommentSerializer, OrdersCommentCommitSerializer
from users.models import Address
from .models import  OrderInfo, OrderGoods

class OrderSettlementView(APIView):
    """"""

    permission_classes = [IsAuthenticated,]

    def get(self, request):
        """
        订单结算商品信息获取:
        1. 从redis中获取用户要结算的商品sku_id和数量count
        2. 根据商品sku_id获取对应商品的信息，组织运费
        3. 将数据序列化并返回
        """
        user = request.user

        # 1. 从redis中获取用户要结算的商品sku_id和数量count
        redis_conn = get_redis_connection('cart')

        # 从redis购物车记录中获取勾选商品sku_id set
        cart_selected_key = 'cart_selected_%s' % user.id
        # (b'<sku_id>, b'<sku_id>', ...)
        sku_ids = redis_conn.smembers(cart_selected_key)

        # 从redis购物车记录中获取用户购物车中商品的sku_id和对应数量count  hash
        cart_key = 'cart_%s' % user.id
        # {
        #     b'<sku_id>': b'<count>',
        #     ...
        # }
        cart_dict = redis_conn.hgetall(cart_key)

        # 组织数据
        # {
        #     '<sku_id>': '<count>',
        #     ...
        # }
        cart = {}
        for sku_id, count in cart_dict.items():
            cart[int(sku_id)] = int(count)

        # 2. 根据商品sku_id获取对应商品的信息，组织运费
        skus = SKU.objects.filter(id__in=sku_ids)

        for sku in skus:
            # 给sku对象增加属性count，保存要结算商品数量count
            sku.count = cart[sku.id]

        # 运费
        freight = Decimal(10)

        # 3. 将数据序列化并返回
        resp = {
            'freight': freight,
            'skus': skus
        }

        serializer = OrderSettlementSerializer(resp)
        return Response(serializer.data)


class SaveOrderView(GenericAPIView):
    """
    保存订单
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SaveOrderSerializer

    def post(self, request):
        """
        订单信息的保存
        1.接收参数并进行校验（参数完整性，地址是否存在，支付方式是否合法）
        2.创建并保存订单的数据
        3.返回应答，订单创建成功
        """
        # 1.接收参数并进行校验（参数完整性，地址是否存在，支付方式是否合法）
        address = request.data.get('address')
        print(request.data)

        if address is None:
            return Response({'errmsg': '地址不能为空哦'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            addres = Address.objects.get(id=address,is_deleted=False)
        except Address.DoesNotExist:
            # raise serializers.ValidationError("地址不能为空")
            print(11111111)
            return Response({'errmsg':'地址不能为空哦'},status=status.HTTP_400_BAD_REQUEST)



        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 2.创建并保存订单的数据
        serializer.save()

        # 3.返回应答，订单创建成功
        return Response(serializer.data, status.HTTP_201_CREATED)
    # def post(self, request):
    #     """
    #     订单信息保存(订单创建):
    #     1. 接收参数并进行参数校验(参数完整性，地址是否存在，支付方式是否合法)
    #     2. 保存订单信息
    #     3. 返回应答，订单创建成功
    #     """
    #     # 1. 接收参数并进行参数校验(参数完整性，地址是否存在，支付方式是否合法)
    #
    #     address = request.data.get('address')
    #
    #     try:
    #         address = Address.objects.get(id=address)
    #     except Address.DoesNotExist:
    #         return Response({'res': 1, 'errmsg': '地址错误'},status=status.HTTP_400_BAD_REQUEST)
    #     print(request.data)
    #
    #     serializer = SaveOrderSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     # 2. 保存订单信息(create)
    #     serializer.save(user=request.user)
    #
    #     # 3. 返回应答，订单创建成功
    #     return Response(serializer.data, status=status.HTTP_201_CREATED)

class OrdersCommentSkuView(APIView):
    """
    商品详情页中查看评论信息
    1.通过url地址获取商品的id。

    2.通过id获取到商品的评论相关信息。

    3.将信息序列化并返回。
    """


    def get(self,request,pk):
        skus = OrderGoods.objects.filter(sku_id=pk)
        data = []
        for sku in skus:
            user = sku.order.user

            dict = {'username':user.username,"comment":sku.comment,"score":sku.score}
            data.append(dict)

        return Response(data)

# Create your views here.
# POST /orders/(?P<order_id>\d+)/comments/
class OrdersCommentView(GenericAPIView):
    serializer_class = OrdersCommentCommitSerializer
    permission_classes = [IsAuthenticated]

    def post(self,request,order_id):
        order = OrderGoods.objects.filter(order_id=order_id).first()
        serialzier = self.get_serializer(order,data=request.data)
        serialzier.is_valid(raise_exception=True)
        serialzier.save()
        return Response(serialzier.data)

# GET /orders/(?P<order_id>\d+)/uncommentgoods/
class OrdersUnCommentView(GenericAPIView):
    serializer_class = OrderCommentSerializer
    permission_classes = [IsAuthenticated]

    def get(self,request,order_id):
        order = OrderGoods.objects.filter(order_id=order_id)
        serializer = self.get_serializer(order,many=True)
        return Response(serializer.data)