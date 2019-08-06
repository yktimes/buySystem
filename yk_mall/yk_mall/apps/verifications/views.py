import logging
import random
from rest_framework.views import APIView
from django_redis import get_redis_connection
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from celery_tasks.sms import tasks as sms_tasks

from yk_mall.utils.captcha.captcha import captcha
from . import constants

logger = logging.getLogger('django')

# GET /image_codes/(?P<image_code_id>\d+)/
class ImageCodeView(APIView):
    """图片验证码"""
    def get(self,request,image_code_id):
        # 生成验证码
        name, text, image = captcha.generate_captcha()
        redis_conn = get_redis_connection('image_codes')
        redis_conn.setex('ImageCode_' + image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)
        return HttpResponse(image,content_type='image/jpg')


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
          3. 使用阿里短信发送短信验证码
          4. 返回应答，发送短信成功
        """
        image_code = request.GET.get('text')
        image_code_id = request.GET.get('image_code_id')
        redis_image = get_redis_connection('image_codes')
        if image_code and image_code_id:
            try:
                real_image_code = redis_image.get("ImageCode_" + image_code_id)
                # 如果图片验证码取出成功,那么删除redis中的缓存.
                if real_image_code:
                    real_image_code = real_image_code.decode()
                    redis_image.delete("ImageCode_" + image_code_id)
            except Exception as e:
                logger.info(e)
                return Response({'message': '获取图片验证码失败'}, status=status.HTTP_400_BAD_REQUEST)
            # 判断图片验证码是否已经过期
            if not real_image_code:
                # 过期
                return Response({'message': '图片验证码已过期'}, status=status.HTTP_400_BAD_REQUEST)
            # 进行图片验证码的校验
            if image_code.lower() != real_image_code.lower():
                # 验证码输入有误
                return Response({'message': '图片验证码输入有误'}, status=status.HTTP_400_BAD_REQUEST)


        # 判断60s之内是否给`mobile`发送过短信
        redis_conn = get_redis_connection('verify_codes')
        send_flag = redis_conn.get('send_flag_%s' % mobile)

        if send_flag:
            return Response(
                {"message":"请求次数太频繁，休息一会吧..."},
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


