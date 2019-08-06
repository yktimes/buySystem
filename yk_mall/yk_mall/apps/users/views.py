from datetime import datetime
import json

from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView,RetrieveAPIView,UpdateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import ObtainJSONWebToken,jwt_response_payload_handler
from django_redis import get_redis_connection
from itsdangerous import TimedJSONWebSignatureSerializer as TJWSSerializer, BadData
from django.conf import settings
from rest_framework.generics import GenericAPIView

from goods.serializers import SKUSerializer
from carts.utils import merge_cookie_cart_to_redis
from . import constants
from .models import User
from . import serializers
from goods.models import SKU
# Create your views here.





class UserAuthorizeView(ObtainJSONWebToken):
    """登录视图"""
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # 登录成功
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            response = Response(response_data)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.utcnow() +
                              api_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                    token,
                                    expires=expiration,
                                    httponly=True)

            # 补充购物车记录合并的过程: 调用合并购物车记录函数
            merge_cookie_cart_to_redis(request, user, response)

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# url(r'^usernames/(?P<username>\w{5,20})/count/$', views.UsernameCountView.as_view()),
class UsernameCountView(APIView):
    """
    用户名数量
    """
    def get(self,request,username):
        users_counts = User.objects.filter(username=username).count()

        data = {
            'username': username,
            'count': users_counts
        }

        return Response(data)


# url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
class MobileCountView(APIView):
    """
    手机号数量
    """
    def get(self, request, mobile):
        """
        获取指定手机号数量
        """

        mobile_counts = User.objects.filter(mobile=mobile).count()
        data = {
                    'mobile': mobile,
                    'count': mobile_counts
                }

        return Response(data)


# url(r'^users/$', views.UserView.as_view()),
class UserView(CreateAPIView):
    """
    用户注册
    传入参数：
        username, password, password2, sms_code, mobile, allow
    """
    serializer_class = serializers.CreateUserSerializer


class UserDetailView(RetrieveAPIView):
    """
    用户详情
    """
    serializer_class = serializers.UserDetailSerializer
    permission_classes = [IsAuthenticated,]

    def get_object(self):
        return self.request.user

class EmailView(UpdateAPIView):
    """
    保存用户邮箱
    """

    serializer_class = serializers.EmailSerializer
    permission_classes = [IsAuthenticated,]

    def get_object(self, *args, **kwargs):
        return self.request.user


# url(r'^emails/verification/$', views.VerifyEmailView.as_view()),
class VerifyEmailView(APIView):
    """
    邮箱验证
    """

    def put(self,request):
        token = request.query_params.get("token")

        if not token:
            return Response({'message':"缺少token"},status=status.HTTP_400_BAD_REQUEST)

        # 验证token
        user = User.check_verify_email_token(token)
        if user is None:
            return Response({'message': '链接信息无效'}, status=status.HTTP_400_BAD_REQUEST)

        user.email_active = True
        user.save()

        return Response({'message': 'OK'})



class AddressViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, GenericViewSet):
    """
    用户地址新增与修改
    """
    serializer_class = serializers.UserAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    # GET /addresses/
    def list(self,request,*args,**kwargs):
        """
        用户地址列表数据
        """

        queryset = self.get_queryset()
        serializer  = self.get_serializer(queryset,many=True)

        user = self.request.user

        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })

        # POST /addresses/

    def create(self, request, *args, **kwargs):
        """
        保存用户地址数据
        """
        # 检查用户地址数据数目不能超过上限

        count = request.user.addresses.filter(is_deleted=False).count()

        if count>=constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({'message': '保存地址数据已达到上限'}, status=status.HTTP_400_BAD_REQUEST)

        return super().create(request,*args,**kwargs)

        # delete /addresses/<pk>/

    def destroy(self, request, *args, **kwargs):
        """
        处理删除
        """
        address = self.get_object()

        address.is_deleted=True


        # if user.default_address.pk == address.pk:
        #     user.default_address=None
        #     user.save()
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

        # put /addresses/pk/status/

    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """

        address = self.get_object()

        request.user.default_address = address
        request.user.save()

        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

        # put /addresses/pk/title/
        # 需要请求体参数 title

    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题
        """

        address = self.get_object()
        serializer = serializers.AddressTitleSerializer(instance=address,data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)




class UserBrowsingHistoryView(mixins.CreateModelMixin,GenericAPIView):
    """
    用户浏览历史记录
     获取用户浏览记录:
        1. 从redis中获取用户浏览的商品的id
        2. 根据商品id获取对应商品的信息
        3. 将商品的信息序列化并返回

    """
    serializer_class = serializers.AddUserBrowsingHistorySerializer
    permission_classes = [IsAuthenticated]

    def post(self,request):

        """保存"""

        # 使用序列化器验证数据
        # 保存 并 返回
        return self.create(request)

    def get(self,request):
        user_id = request.user.id


        redis_conn = get_redis_connection('history')

        history = redis_conn.lrange('history_%s'%user_id,0,constants.USER_BROWSING_HISTORY_COUNTS_LIMIT-1)


        skus = []

        for sku_id in history:
            sku = SKU.objects.get(id=sku_id)
            skus.append(sku)


        s = SKUSerializer(skus,many=True)

        return Response(s.data)


# PUT /users/(?P<pk>\d+)/password/
class UserPasswordChangeView(GenericAPIView):

    serializer_class = serializers.UserPasswordChangeSerializer
    permission_classes = [IsAuthenticated,]

    def post(self,request,pk):
        """
        1.在模型类中实现检验修改密码 token 的方法，取出 data，判断 user_id 是否一样；

        2.判断两次密码是否一样，判断是否是当前用户，返回数据；

        3.更新密码；

        4.返回重置密码成功信息。

        """
        user = User.objects.filter(id=pk).first()
        json_str = request.body
        json_str = json_str.decode()  # python3.6 无需执行此步
        req_data = json.loads(json_str)
        access_token = req_data.get('access_token')

        # 对ｔｏｋｅｎ进行解密
        sec = TJWSSerializer(settings.SECRET_KEY, 300)
        try:
            data = sec.loads(access_token)
        except BadData:
            return Response('非法请求')
        user_id = data.get('user_id')

        if user_id == int(pk):
            # 判断两次密码是否一致
            if req_data['password'] != req_data['password2']:
                return Response('两次密码不一样，请仔细检查一下下...')
            user.set_password(req_data['password'])
            user.save()
            return Response({'id':user_id,'username':user.username,'mobile':user.mobile})
        return Response('非法请求')
    def put(self,request,pk):
        """
        1.获取参数并校验，看原密码是否正确，两次密码是否一致。
        2.获取当前用户信息，更新到数据库。
        3.返回响应。
        """
        # 1.获取参数并校验，看原密码是否正确，两次密码是否一致。
        user = request.user

        # 2.获取参数并进行校验
        serializer = self.get_serializer(user,data = request.data)
        serializer.is_valid(raise_exception=True)

        # 3.保存修改地址的数据
        serializer.save()
        # 4.返回应答，修改成功
        return Response({'message':'OK'})

