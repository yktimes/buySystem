# 自定义文件存储类
from django.conf import settings
from django.core.files.storage import Storage, FileSystemStorage
from django.utils.deconstruct import deconstructible
from fdfs_client.client import Fdfs_client


@deconstructible
class FDFSStorage(Storage):
    """FDFS文件存储类"""
    def __init__(self, base_url=None, client_conf=None):
        """
        初始化
        base_url: 用于构造图片完整路径使用，图片服务器的域名
        client_conf: FastDFS客户端配置文件的路径
        """
        if base_url is None:
            base_url = settings.FDFS_URL

        self.base_url = base_url

        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF

        self.client_conf = client_conf

    def _save(self, name, content):
        """
        name: 用户选择上传文件的名称: 1.jpg
        content: 包含上传文件内容的File对象，通过content.read()获取上传文件内容
        """
        # 将文件上传到FDFS系统
        client = Fdfs_client(self.client_conf)

        res = client.upload_by_buffer(content.read())

        # 判断上传是否成功
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到FDFS系统失败')

        # 获取文件id
        file_id = res.get('Remote file_id')

        return file_id

    def exists(self, name):
        """
        判断用户上传文件的名字和文件存储系统的原有文件是否冲突:
        name: 用户选择上传文件的名称: 1.jpg
        """
        return False

    def url(self, name):
        """
        返回可访问到文件的完整的url地址:
        name: 表中图片字段存放的内容
        """
        return self.base_url + name

