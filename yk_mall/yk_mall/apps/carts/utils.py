import pickle
import base64
from django_redis import get_redis_connection


def merge_cookie_cart_to_redis(request, user, response):
    """合并cookie中购物车数据到redis数据库"""
    # 获取客户端浏览器发送过来的cookie购物车数据
    cookie_cart = request.COOKIES.get('cart') # None

    if cookie_cart is None:
        return

    # 解析cookie中购物车数据
    # {
    #     '<sku_id>': {
    #         'count': '<count>',
    #         'selected': '<selected>'
    #     },
    #     ...
    # }
    cart_dict = pickle.loads(base64.b64decode(cookie_cart)) # {}

    if not cart_dict:
        return

    # 处理数据
    # 保存cookie购物车记录中商品的sku_id和数量count，在合并时将数据添加到redis对应hash元素中
    # {
    #     '<sku_id>': '<count>',
    #     ...
    # }
    cart = {}

    # 保存cookie购物车记录中被勾选商品的sku_id，在合并时将这些商品sku_id添加到redis对应set元素中
    redis_cart_add = []

    # 保存cookie购物车记录中未被勾选商品的sku_id，在合并时将这些商品sku_id从redis对应set元素中移除
    redis_cart_remove = []

    for sku_id, count_selected in cart_dict.items():
        cart[sku_id] = count_selected['count']

        if count_selected['selected']:
            # 勾选
            redis_cart_add.append(sku_id)
        else:
            # 未勾选
            redis_cart_remove.append(sku_id)

    # 进行合并
    # 获取redis链接
    redis_conn = get_redis_connection('cart')
    pl = redis_conn.pipeline()

    # 合并购物车中商品的sku_id和对应数量count   hash
    cart_key = 'cart_%s' % user.id
    # hmset(key, dict): 将dict中key和value作为属性和值设置到redis中hash元素中
    # 如果属性已存在，进行覆盖，如果属性不存在，创建新的属性和值
    pl.hmset(cart_key, cart)

    # 合并购物车中商品勾选状态
    cart_selected_key = 'cart_selected_%s' % user.id

    if redis_cart_add:
        # 将sku_id添加到redis对应set元素中
        # sadd(key, *members)
        pl.sadd(cart_selected_key, *redis_cart_add)

    if redis_cart_remove:
        # 将sku_id从redis对应set元素中移除
        # srem(key, *members)
        pl.srem(cart_selected_key, *redis_cart_remove)

    pl.execute()

    # 清除cookie中的购物车数据
    response.delete_cookie('cart')
