class QQAPIError(Exception):
    """QQ接口调用异常"""

    def __init__(self, message):
        self.message = message


if __name__ == "__main__":
    # 测试代码
    e = QQAPIError({'code': 1001, 'message': '错误信息'})
    print(e.message)
    print(type(e.message))
