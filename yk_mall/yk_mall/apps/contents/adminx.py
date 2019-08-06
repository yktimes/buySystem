import xadmin
from xadmin import views
from .models import ContentCategory,Content

class ContentCategoryAdmin:
    """
    广告内容类别
    """


    list_display = ['name', 'key']
    search_fields = ['name', 'key']
    list_filter = ['name', 'key']
    list_editable = ['name', 'key']
    show_detail_fields = ['name', 'key']



class ContentAdmin:
    """
    广告内容
    """
    list_display = ['title', 'category','url','image','text','sequence','status']
    search_fields = ['title', 'status']
    list_filter = ['category', 'status']
    list_editable = ['title', 'url','image','text','sequence','status']
    show_detail_fields = ['title', 'category']





xadmin.site.register(ContentCategory,ContentCategoryAdmin)
xadmin.site.register(Content,ContentAdmin)
