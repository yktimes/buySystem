from collections import OrderedDict
from django.conf import settings
from django.template import loader
import os
import time

from goods.models import GoodsChannel
from contents.models import ContentCategory

from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import *

# from goods.serializers import  GoodsCategorySerializer
class IndexView(APIView):

    def get(self,request):


        """
        生成静态的主页html文件
        """

        # 从数据库中查询首页所需要数据(商品分类数据&广告数据)
        # 商品频道及分类菜单
        # 使用有序字典保存类别的顺序
        # categories = {
        #     1: { # 组1
        #         'channels': [{'id':, 'name':, 'url':},{}, {}...],
        #         'sub_cats': [{'id':, 'name':, 'sub_cats':[{},{}]}, {}, {}, ..]
        #     },
        #     2: { # 组2
        #
        #     }
        # }
        categories = OrderedDict()
        channels = GoodsChannel.objects.order_by('group_id', 'sequence')
        print(111111111111,channels)
        for channel in channels:
            group_id = channel.group_id  # 当前组
            print("group_id",group_id)
            if group_id not in categories:
                categories[group_id] = {'channels': [], 'sub_cats': []}

            cat1 = channel.category  # 当前频道的类别
            print("c1",cat1)
            # 追加当前频道
            categories[group_id]['channels'].append({
                'id': cat1.id,
                'name': cat1.name,
                'url': channel.url
            })

            print(cat1)

            # # 构建当前类别的子类别
            for cat2 in cat1.goodscategory_set.all():
                print("car2",cat2)
                cat2.sub_cats = []
                print("2   ",cat2)
                # print(GoodsCategorySerializer(cat2,many=True).data)
                for cat3 in cat2.goodscategory_set.all():
                    print(cat3.name)
                    cat2.sub_cats.append([cat3.id,cat3.name])
                    print("cat2.sub_cats",cat2.sub_cats)
                    print('2  ',cat2)

                categories[group_id]['sub_cats'].append([cat2.name,cat2.sub_cats])
            #
            #     print("ccc", categories)

            # 广告内容
        # contents = {}
        # content_categories = ContentCategory.objects.all()
        # for cat in content_categories:
        #     contents[cat.key] = ContentSerializer(cat.content_set.filter(status=True).order_by('sequence'), many=True)

        # 广告内容
        contents = {}
        content_categories = ContentCategory.objects.all()
        for cat in content_categories:
            c = ContentSerializer(cat.content_set.filter(status=True).order_by('sequence'),many=True)
            print("6",c.data)
            contents[cat.key] = c.data
            # print(contents)
            # contents.update(c.data)
        # 使用index.html模板文件，进行模板渲染，产生替换之后的内容
        context = {
            'categories': categories,
            'contents': contents,

        }

        print("111",context)
        # 1. 加载模板文件: 指定使用的模板文件，获取模板对象


        return Response(context)
