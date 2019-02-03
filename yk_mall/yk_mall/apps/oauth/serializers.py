from rest_framework import serializers
from users.models import User
from .utils import OAuthQQ
from rest_framework.settings import api_settings
from .models import OAuthQQUser
from django_redis import get_redis_connection


from django_redis import get_redis_connection
from rest_framework import serializers




class OAuthQQUserSerializer(serializers.ModelSerializer):
    sms_code = serializers.CharField(label='短信验证码', write_only=True)
    access_token = serializers.CharField(label='操作token', write_only=True)
    token = serializers.CharField(label='JWT token', read_only=True)
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$', write_only=True)

    class Meta:
        model = User
        fields = ('id', 'mobile', 'password', 'sms_code', 'access_token', 'username', 'token')

        extra_kwargs = {
            'password': {
                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            },
            'username': {
                'read_only': True
            }
        }

    def validate(self, attrs):
        """access_token是有效，短信验证是否正确"""
        # access_token是有效
        access_token = attrs['access_token']

        openid = OAuthQQ.check_save_user_token(access_token)

        if openid is None:
            raise serializers.ValidationError('无效的access_token')

        attrs['openid'] = openid

        # 短信验证是否正确
        # 获取真实的短信验证码内容
        mobile = attrs['mobile']
        redis_conn = get_redis_connection('verify_codes')
        real_sms_code = redis_conn.get('sms_%s' % mobile)  # bytes

        if not real_sms_code:
            raise serializers.ValidationError('短信验证码已过期')

        # 对比
        sms_code = attrs['sms_code']  # str
        real_sms_code = real_sms_code.decode()  # str
        if sms_code != real_sms_code:
            raise serializers.ValidationError('短信验证码错误')

        # 如果`mobile`已注册，校验对应的密码是否正确
        mobile = attrs['mobile']

        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 未注册，pass
            user = None
        else:
            # 已注册，校验对应的密码是否正确
            password = attrs['password']
            if not user.check_password(password):
                raise serializers.ValidationError('登录密码错误')

        # 给attrs字典中增加一条数据user，保存用户，以便在create中进行使用
        attrs['user'] = user

        return attrs

    def create(self, validated_data):
        """保存绑定QQ登录用户的信息，签发jwt token"""
        # 2.1 如果用户已注册，直接保存绑定信息
        # 2.2 如果用户未注册，先创建一个新用户，然后在保存绑定信息
        user = validated_data['user']

        if user is None:
            # 未注册
            mobile = validated_data['mobile']
            password = validated_data['password']
            user = User.objects.create_user(username=mobile, mobile=mobile, password=password)

        # 保存绑定信息
        openid = validated_data['openid']
        OAuthQQUser.objects.create(
            user=user,
            openid=openid
        )

        # 签发jwt token
        # 由服务器签发一个jwt token，保存用户身份信息

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

        # 生成载荷信息(payload)
        payload = jwt_payload_handler(user)
        # 生成jwt token
        token = jwt_encode_handler(payload)

        # 给user对象增加一个属性token，保存jwt token信息
        user.token = token

        return user

