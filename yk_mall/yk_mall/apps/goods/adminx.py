import xadmin
from xadmin import views

from . import models




class BaseSetting(object):
    """xadmin的基本配置"""
    enable_themes = True  # 开启主题切换功能
    use_bootswatch = True

xadmin.site.register(views.BaseAdminView, BaseSetting)


class GlobalSettings(object):
    """xadmin的全局配置"""
    site_title = "商城运营管理系统"  # 设置站点标题
    site_footer = "商城集团有限公司"  # 设置站点的页脚


xadmin.site.register(views.CommAdminView, GlobalSettings)


class SKUAdmin(object):
    """商品Admin管理类"""
    model_icon = 'fa fa-gift'
    list_display = ['id', 'name', 'price', 'stock','is_launched', 'sales', 'comments']
    search_fields = ['id','name']
    list_filter = ['category','is_launched']
    list_editable = ['price', 'stock','is_launched']
    show_detail_fields = ['name']
    readonly_fields = ['sales', 'comments']

    data_charts = {
        "sku_amount": {'title': '库存', "x-field": "id", "y-field": ('stock',),
                        },
        "sales_count": {'title': '销量', "x-field": "id", "y-field": ('sales',),
                        },
    }

class SKUSpecificationAdmin(object):
    model_icon = 'fa fa-gift'
    list_display = ['sku', 'spec', 'option']

    list_filter = ['sku']
    show_detail_fields = ['sku','spec', 'option']

    def save_models(self):
        # 保存数据对象
        obj = self.new_obj
        obj.save()

        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html.delay(obj.sku.id)

    def delete_model(self):
        # 删除数据对象
        obj = self.obj
        sku_id = obj.sku.id
        obj.delete()

        from celery_tasks.html.tasks import generate_static_sku_detail_html
        generate_static_sku_detail_html.delay(sku_id)


class SKUImageAdmin(object):
    """商品图片Admin管理类"""
    model_icon = 'fa fa-gift'
    list_display = ['sku', 'image']
    search_fields = ['image']
    list_filter = ['sku']
    list_editable = ['image']
    show_detail_fields = ['sku', 'image']

class GoodsAdmin(object):
    """Goods Admin管理类"""
    model_icon = 'fa fa-gift'
    list_display = ['name', 'brand','sales','category1','category2','category3']
    search_fields = ['name']
    list_filter = ['brand','category1','category2','category3']
    list_editable = ['name','category1','category2','category3']
    show_detail_fields = ['name']


"""
list_display 控制列表展示的字段
search_fields 控制可以通过搜索框搜索的字段名称，xadmin使用的是模糊查询
list_filter 可以进行过滤操作的列
ordering 默认排序的字段
readonly_fields 在编辑页面的只读字段
exclude 在编辑页面隐藏的字段
list_editable 在列表页可以快速直接编辑的字段
show_detail_fileds 在列表页提供快速显示详情信息

"""
class BrandAdmin(object):
    """品牌Admin管理类"""
    model_icon = 'fa fa-gift'
    list_display = ['name', 'logo','first_letter']
    search_fields = ['name', 'first_letter']
    list_filter = ['name']
    list_editable = ['name','logo']
    show_detail_fields = ['name']

class GoodsSpecificationAdmin:
    """
    商品规格
    """
    model_icon = 'fa fa-gift'
    list_display = ['goods', 'name']
    search_fields = ['name']
    list_filter = ['name']
    list_editable = ['name']
    show_detail_fields = ['name']


class SpecificationOptionAdmin():
    """'规格选项'"""
    model_icon = 'fa fa-gift'
    list_display = ['spec', 'value']
    search_fields = ['value']
    list_filter = ['spec', 'value']
    list_editable = ['spec', 'value']
    show_detail_fields = ['spec', 'value']

class GoodsCategoryAdmin:
    """
    商品类别
    """
    model_icon = 'fa fa-gift'
    list_display = ['name', 'parent']
    search_fields = ['name']
    list_filter = ['name', 'parent']
    list_editable = ['name', 'parent']
    show_detail_fields = ['name', 'parent']



class GoodsChannelAdmin:
    """
    商品频道
    """

    model_icon = 'fa fa-gift'
    list_display = ['group_id', 'category','url','sequence']
    search_fields = ['group_id']
    list_filter = ['category', 'sequence']
    list_editable = ['url', 'sequence','group_id']
    show_detail_fields = ['group_id', 'parent']



# 注册模型类
xadmin.site.register(models.SKU, SKUAdmin)
xadmin.site.register(models.SKUSpecification, SKUSpecificationAdmin)
xadmin.site.register(models.Goods,GoodsAdmin)
xadmin.site.register(models.SKUImage,SKUImageAdmin)
xadmin.site.register(models.Brand,BrandAdmin)
xadmin.site.register(models.GoodsSpecification,GoodsSpecificationAdmin)

xadmin.site.register(models.SpecificationOption,SpecificationOptionAdmin)


xadmin.site.register(models.GoodsCategory,GoodsCategoryAdmin)
xadmin.site.register(models.GoodsChannel,GoodsChannelAdmin)






