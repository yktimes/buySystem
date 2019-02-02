from rest_framework import serializers
from .models import User
import re
from django_redis import get_redis_connection

class CreateUserSerializer(serializers.ModelSerializer):
    """
     创建用户序列化器
     """

    password2 = serializers.CharField(label='确认密码',write_only=True)
    sms_code = serializers.CharField(label='短信验证码',write_only=True)
    allow = serializers.CharField(label='同意协议',write_only=True)


    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'sms_code', 'mobile', 'allow')
        extra_kwargs={

            'username':{
                'min_length':6,
                'max_length':20,
                'error_messages':{
                    'min_length': '仅允许5-20个字符的用户名',
                    'max_length': '仅允许5-20个字符的用户名',
                }
            },
            'password':{

                'write_only': True,
                'min_length': 8,
                'max_length': 20,
                'error_messages': {
                    'min_length': '仅允许8-20个字符的密码',
                    'max_length': '仅允许8-20个字符的密码',
                }
            }
        }

    def validate_mobile(self,value):
        """验证手机号"""
        if not re.match(r'^1[3-9]\d{9}$',value):
            raise serializers.ValidationError("手机号格式错误")

        # 手机号重复

        count = User.objects.filter(mobile=value).count()
        if count>0:
            raise serializers.ValidationError('手机号存在')

        # 注意单个字段验证一定要记得返回,不然　validate 收不到数据了
        return value

    def validate_allow(self,value):
        if value!='true':
            raise serializers.ValidationError("请同意用户协议")

        return value

    def validate(self,data):
        # 判断两次密码

        if data['password']!=data['password2']:
            raise serializers.ValidationError("两次密码不一致")


        #　判断短信验证码
        redis_conn = get_redis_connection('verify_codes')
        mobile = data['mobile']
        print(mobile)
        real_sms_code  = redis_conn.get("sms_%s"%mobile)
        print(real_sms_code)
        if real_sms_code is None:
            raise serializers.ValidationError("无效的短信验证码")

        if data['sms_code']!=real_sms_code.decode():
            raise serializers.ValidationError("短信验证码错误")

        return data

    def create(self,validated_data):
        """创建用户"""

        del validated_data['allow']
        del validated_data['password2']
        del validated_data['sms_code']

        user = super().create(validated_data)

        # 调用django的认证系统
        user.set_password(validated_data['password'])

        user.save()


        return user