from django.conf.urls import url
from . import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('skus/search', views.SKUSearchViewSet, base_name='skus_search')




urlpatterns = [

    url(r'^categories/(?P<category_id>\d+)/skus/$', views.SKUListView.as_view()),
    url(r'^orders/user/$', views.UserOrdersView.as_view({'get': 'list'})),
]



urlpatterns += router.urls