import os

from django.conf import settings
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from alipay import AliPay

from orders.models import OrderInfo
from .models import Payment
# Create your views here.


# http://www.meiduo.site:8080/pay_success.html?
# charset=utf-8&
# out_trade_no=201809070846570000000002& # 订单编号
# method=alipay.trade.page.pay.return&
# total_amount=3798.00&
# 签名字符串
# sign=M9mbWeX%2FqQdIyYqd5MqrMiHdNuIJHak8rlE7LsrMb0qtrMl93C9NJg%2BuEhesIaiunAqKPYyg37aQIx%2FvqaejResVs3h%2BA4kuVISlnfVMF9b0x%2FYzd%2BJ3Cyxvh7LG%2BXABK734B5QHnORsWD%2FoVySj9NumXYyEinSZ4Ag4KrHNkp7csE3%2FjCPFe%2B%2B1gzr2BL5fijZYwAOCOF9dERNx61JhoNI4ACYI029P3G6iw16J7CfFZXrutjb7YQJVOR6ISH5OAPhr%2FdoH8cPGRxDHDk9pICvu1tThLn%2FDPdnLubdUyWOogt6NklBsUWdd0gtoXHBrfM1wJFnip5FANsS1cFNr0Q%3D%3D&
# trade_no=2018090721001004920200663882& # 支付宝交易号
# auth_app_id=2016090800464054&
# version=1.0&
# app_id=2016090800464054&
# sign_type=RSA2&
# seller_id=2088102174694091&
# timestamp=2018-09-07+08%3A48%3A39


# PUT /payment/status/?支付宝参数
class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        """
        保存支付结果:
        1. 验证签名
        2. 根据订单id校验订单是否有效
        3. 保存支付结果
        4. 返回应答
        """
        # 1. 验证签名
        data = request.query_params.dict() # QueryDict->dict
        signature = data.pop('sign')

        # 初始化
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,  # 应用APPID
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )

        success = alipay.verify(data, signature)

        if not success:
            return Response({'message': '非法请求'}, status=status.HTTP_403_FORBIDDEN)

        # 2. 根据订单id校验订单是否有效
        user = request.user
        order_id = data.get('out_trade_no')
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=user,
                pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'], # 支付宝支付
                status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'], # 待支付
            )
        except OrderInfo.DoesNotExist:
            return Response({'message': '无序的订单信息'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 保存支付结果
        # 获取支付交易号
        trade_id = data.get('trade_no')
        Payment.objects.create(
            order=order,
            trade_id=trade_id
        )

        # 更改订单的状态
        order.status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] # 待发货
        order.save()

        # 4. 返回应答
        return Response({'trade_id': trade_id})


# GET /orders/(?P<order_id>\d+)/payment/
class PaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        """
        获取支付宝支付网址和参数:
        1. 根据订单id校验订单是否有效
        2. 组织支付宝支付网址和参数
        3. 返回支付支付网址
        """
        user = request.user
        # 1. 根据订单id校验订单是否有效
        try:
            order = OrderInfo.objects.get(
                order_id=order_id,
                user=user,
                pay_method=OrderInfo.PAY_METHODS_ENUM['ALIPAY'], # 支付宝支付
                status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'], # 待支付
            )
        except OrderInfo.DoesNotExist:
            return Response({'message': '无序的订单信息'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 组织支付宝支付网址和参数
        # 初始化
        alipay = AliPay(
            appid=settings.ALIPAY_APPID, # 应用APPID
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )

        # 组织支付参数
        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        total_amount = order.total_amount # Decimal
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id, # 商户订单号
            total_amount=str(total_amount), # 订单总金额
            subject='美多商城%s' % order_id, # 订单标题
            return_url="http://www.meiduo.site:8080/pay_success.html",
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 3. 返回支付支付网址
        pay_url = settings.ALIPAY_URL + '?' + order_string
        return Response({'alipay_url': pay_url})