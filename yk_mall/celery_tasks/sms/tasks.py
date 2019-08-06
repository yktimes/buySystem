import logging
from yk_mall.utils.aliyunsdk import aliyunsms
from celery_tasks.main import celery_app

from . import constants

logger = logging.getLogger('django')

# # 验证码短信模板
# SMS_CODE_TEMP_ID = 1


@celery_app.task(name='send_sms_code')
def send_sms_code(mobile, code, expires=None):
    """
    发送短信验证码
    :param mobile: 手机号
    :param code: 验证码
    :param expires: 有效期
    :return: None
    """

    try:
        result = aliyunsms.send_sms(mobile, code)
        print("短信",result)
        logger.info("发送验证码短信[正常][ result: %s ]" % result)
        # ccp = CCP()
        # result = ccp.send_template_sms(mobile, [code, expires], constants.SMS_CODE_TEMP_ID)
    except Exception as e:
        logger.error("发送验证码短信[异常][ mobile: %s, message: %s ]" % (mobile, e))
    else:
        if result == 0:
            logger.info("发送验证码短信[正常][ mobile: %s ]" % mobile)
        else:
            logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile)