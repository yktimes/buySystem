from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView,RetrieveAPIView,UpdateAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework.decorators import action


from django_redis import get_redis_connection
from . import constants
from .models import User
from . import serializers
from goods.models import SKU
# Create your views here.

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



from rest_framework.generics import GenericAPIView
from goods.serializers import SKUSerializer
class UserBrowsingHistoryView(mixins.CreateModelMixin,GenericAPIView):
    """
    用户浏览历史记录
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




