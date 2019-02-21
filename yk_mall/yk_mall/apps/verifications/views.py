from django.shortcuts import render
from rest_framework.views import APIView
from django_redis import get_redis_connection
from rest_framework.response import Response
from rest_framework import status
import random
from . import constants

from yk_mall.libs.yuntongxun.sms import CCP
from celery_tasks.sms import tasks as sms_tasks
# Create your views here.

# url('^sms_codes/(?P<mobile>1[3-9]\d{9})/$', views.SMSCodeView.as_view()),

class SMSCodeView(APIView):
    """
      短信验证码
      传入参数：mobile
    """

    def get(self,request,mobile):
        """
          获取短信验证码:
          1. 生成短信验证码内容
          2. 在redis中保存短信验证码内容，以`mobile`为key，以短信验证码内容为value
          3. 使用云通讯发送短信验证码
          4. 返回应答，发送短信成功
        """

        # 判断60s之内是否给`mobile`发送过短信
        redis_conn = get_redis_connection('verify_codes')
        send_flag = redis_conn.get('send_flag_%s' % mobile)

        if send_flag:
            return Response(
                {"message":"请求次数太频繁"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 生成短信验证码
        sms_code = "%06d"%random.randint(0,999999)

        # 保存短信验证码和发送记录

        pl = redis_conn.pipeline()

        pl.setex('sms_%s'%mobile,constants.SMS_CODE_REDIS_EXPIRES,sms_code)
        pl.setex('send_flag_%s'%mobile,constants.SEND_SMS_CODE_INTERVAL,1)
        pl.execute()


        # 发送短信验证码

        sms_code_expires = constants.SMS_CODE_REDIS_EXPIRES // 60
        sms_tasks.send_sms_code.delay(mobile,sms_code,sms_code_expires)


        return Response({'message':'ok'})


