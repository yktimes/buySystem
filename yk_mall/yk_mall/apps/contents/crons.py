
from collections import OrderedDict
from django.conf import settings
from django.template import loader
import os
import time

from goods.models import GoodsChannel
from contents.models import ContentCategory


def generate_static_index_html():

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
    for channel in channels:
        group_id = channel.group_id  # 当前组

        if group_id not in categories:
            categories[group_id] = {'channels': [], 'sub_cats': []}

        cat1 = channel.category  # 当前频道的类别

        # 追加当前频道
        categories[group_id]['channels'].append({
            'id': cat1.id,
            'name': cat1.name,
            'url': channel.url
        })
        # 构建当前类别的子类别
        for cat2 in cat1.goodscategory_set.all():
            cat2.sub_cats = []
            for cat3 in cat2.goodscategory_set.all():
                cat2.sub_cats.append(cat3)
            categories[group_id]['sub_cats'].append(cat2)

    # 广告内容
    contents = {}
    content_categories = ContentCategory.objects.all()
    for cat in content_categories:
        contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

    url = settings.FDFS_URL
    # 使用index.html模板文件，进行模板渲染，产生替换之后的内容
    context = {
        'categories': categories,
        'contents': contents,
        'url':url
    }

    # 1. 加载模板文件: 指定使用的模板文件，获取模板对象

    temp = loader.get_template('index.html')

    # 2. 模板渲染: 将模板文件中变量进行替换，返回替换之后的页面内容
    res_html = temp.render(context)

    print('%s: generate_static_index_html' % time.ctime(),context)
    # 将替换之后的内容保存成静态index.html文件
    save_path = os.path.join(settings.GENERATED_STATIC_HTML_FILES_DIR, 'index.html')

    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(res_html)

