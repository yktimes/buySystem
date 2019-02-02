import re
from .models import *
from django.contrib.auth.backends import ModelBackend

# 自定义jwt认证 返回　token 和　id name
def jwt_response_payload_handler(token, user=None, request=None):
    """
    自定义jwt认证成功返回数据
    """
    return {
        'token': token,
        'user_id': user.id,
        'username': user.username
    }


def get_user_by_account(account):
    """
    根据帐号获取user对象
    :param account: 账号，可以是用户名，也可以是手机号
    :return: User对象 或者 None
    """
    try:
        if re.match(r"^1[3-9]\d{9}$",account):
            # 账号为手机
            user=User.objects.get(mobile=account)
        else:
            # 账号为用户名
            user=User.objects.get(username=account)
    except User.DoesNotExist:
        return None

    return user

"""
修改Django认证系统的认证后端需要继承django.contrib.auth.backends.ModelBackend，
并重写authenticate方法
"""

class UsernameMobileAuthBackend(ModelBackend):
    """
    自定义用户名或手机号认证
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        user = get_user_by_account(username)
        if user is not None and user.check_password(password):
            return user

"""
重写authenticate方法的思路：

根据username参数查找用户User对象，username参数可能是用户名，也可能是手机号
若查找到User对象，调用User对象的check_password方法检查密码是否正确
"""