import xadmin
# Register your models here.

from .models import User
from xadmin.plugins import auth


class UserAdmin(auth.UserAdmin):

    list_display = ('username','mobile', 'email',  'is_staff','last_login','default_address')
    list_filter = ('is_staff', 'is_superuser', 'is_active','last_login')
    search_fields = ('username', 'email','last_login')
    ordering = ('username',)
    list_editable=('username','mobile', 'email', 'is_staff',)
    style_fields = {'user_permissions': 'm2m_transfer', 'groups': 'm2m_transfer'}

    def get_model_form(self, **kwargs):
        if self.org_obj is None:
            self.fields = ['username', 'mobile', 'is_staff']

        return super().get_model_form(**kwargs)





xadmin.site.unregister(User)
xadmin.site.register(User, UserAdmin)