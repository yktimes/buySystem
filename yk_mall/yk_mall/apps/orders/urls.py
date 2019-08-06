from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^orders/settlement/$', views.OrderSettlementView.as_view()),
    url(r'^orders/$', views.SaveOrderView.as_view()),
    url(r'^orders/(?P<order_id>\d+)/uncommentgoods/$',views.OrdersUnCommentView.as_view()),
    url(r'^orders/(?P<order_id>\d+)/comments/$',views.OrdersCommentView.as_view()),
    url(r'^skus/(?P<pk>\d+)/comments/$',views.OrdersCommentSkuView.as_view()),



]