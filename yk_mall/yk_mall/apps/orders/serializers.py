from datetime import datetime

from decimal import Decimal
from django.db import transaction
from django_redis import get_redis_connection
from rest_framework import serializers

from goods.models import SKU
from .models import OrderInfo, OrderGoods
from users.models import Address
from rest_framework.response import Response


class CartSKUSerializer(serializers.ModelSerializer):
    """
    购物车商品数据序列化器
    """
    count = serializers.IntegerField(label='数量')

    class Meta:
        model = SKU
        fields = ('id', 'name', 'default_image_url', 'price', 'count')


class OrderSettlementSerializer(serializers.Serializer):
    """
    订单结算数据序列化器
    """
    freight = serializers.DecimalField(label='运费', max_digits=10, decimal_places=2)
    skus = CartSKUSerializer(many=True)


class SaveOrderSerializer(serializers.ModelSerializer):
    """
    下单数据序列化器
    """
    class Meta:
        model = OrderInfo
        fields = ('order_id', 'address', 'pay_method')
        read_only_fields = ('order_id',)

        extra_kwargs = {
            'address': {
                'write_only': True,
                'required': True,
                # "error_messages": {"required": "不能为空"}


            },
            'pay_method': {
                'write_only': True,
                'required': True,

            }
        }

    def create(self, validated_data):

        print(validated_data)
        """保存订单信息(订单并发-乐观锁)"""
        # 获取参数address和pay_method
        address = validated_data['address']
        pay_method = validated_data['pay_method']




        try:
            addres = Address.objects.get(id=address.pk,is_deleted=False)
        except Address.DoesNotExist:
            raise serializers.ValidationError("地址不能为空")
        print("address",addres)

        print(self.context)

        # 组织参数
        # 用户user
        user = self.context['request'].user

        # 订单id: '年月日时分秒'+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + ('%010d' % user.id)

        # 运费
        freight = Decimal(10)

        # 订单商品总数量和实付款
        total_count = 0
        total_amount = Decimal(0)

        # 订单状态
        # if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH']:
        #     # 货到付款
        #     status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] # 待发货
        # else:
        #     # 在线支付
        #     status = OrderInfo.ORDER_STATUS_ENUM['UNPAID'] # 待支付

        status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH'] else OrderInfo.ORDER_STATUS_ENUM['UNPAID']

        # 获取redis链接
        redis_conn = get_redis_connection('cart')

        # 从redis中获取用户所要购买的商品sku_id  set
        cart_selected_key = 'cart_selected_%s' % user.id
        # (b'<sku_id>', ...)
        sku_ids = redis_conn.smembers(cart_selected_key)

        # 从redis中获取用户购物车商品的sku_id和对应的数量count  hash
        cart_key = 'cart_%s' % user.id
        # {
        #     b'<sku_id>': b'<count>',
        #     ...
        # }
        cart_dict = redis_conn.hgetall(cart_key)

        with transaction.atomic():
            # 在with语句块中代码，凡是涉及到数据库操作的代码，都会放到同一个事务中

            # 设置一个事务保存点
            sid = transaction.savepoint()

            try:
                # 1）向订单基本信息表添加一条记录
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=total_count,
                    total_amount=total_amount,
                    freight=freight,
                    pay_method=pay_method,
                    status=status
                )

                # 2）订单中包含几个商品，就需要向订单商品表中添加几条记录
                for sku_id in sku_ids:
                    # 获取用户所要购买的该商品的数量count
                    count = cart_dict[sku_id]
                    count = int(count)

                    for i in range(3):
                        # 根据sku_id获取商品信息
                        # select * from tb_sku where id=<sku_id>;
                        sku = SKU.objects.get(id=sku_id)

                        # 判断商品库存是否充足
                        if count > sku.stock:
                            # 回滚到sid事务保存点
                            transaction.savepoint_rollback(sid)
                            raise serializers.ValidationError('商品库存不足')

                        # 记录商品原始库存
                        origin_stock = sku.stock
                        new_stock = origin_stock - count
                        new_sales = sku.sales + count

                        # 模拟订单并发问题
                        # print('user: %d times: %s stock: %s' % (user.id, i, origin_stock))
                        # import time
                        # time.sleep(10)

                        # 减少商品库存，增加销量
                        # update tb_sku
                        # set stock=<new_stock>, sales=<new_sales>
                        # where id=<sku_id> and stock=<origin_stock>;
                        # update方法返回的是更新的行数
                        res = SKU.objects.filter(id=sku_id, stock=origin_stock).update(stock=new_stock, sales=new_sales)

                        if res == 0:
                            if i == 2:
                                # 更新了3次，仍然失败，下单失败
                                # 回滚到sid事务保存点
                                transaction.savepoint_rollback(sid)
                                raise serializers.ValidationError('下单失败2')

                            # 更新失败，重新进行尝试
                            continue

                        # 向订单商品表中添加一条记录
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=count,
                            price=sku.price
                        )

                        # 累加计算订单中商品总数量和总金额
                        total_count += count
                        total_amount += sku.price*count

                        # 更新成功，跳出循环
                        break

                # 实付款
                total_amount += freight
                # 更新订单记录中商品的总数量和实付款
                order.total_count = total_count
                order.total_amount = total_amount
                order.save()
            except serializers.ValidationError:
                # 继续向外抛出异常
                raise
            except Exception as e:
                # 回滚sid事务保存点
                transaction.savepoint_rollback(sid)
                raise serializers.ValidationError('下单失败1')

        # 3）清除购物车中对应的记录
        pl = redis_conn.pipeline()
        pl.hdel(cart_key, *sku_ids)
        pl.srem(cart_selected_key, *sku_ids)
        pl.execute()

        # 返回订单对象
        return order

    def create_1(self, validated_data):
        """保存订单信息(订单并发-悲观锁)"""
        # 获取参数address和pay_method
        address = validated_data['address']
        pay_method = validated_data['pay_method']

        # 组织参数
        # 用户user
        user = self.context['request'].user

        # 订单id: '年月日时分秒'+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + ('%010d' % user.id)

        # 运费
        freight = Decimal(10)

        # 订单商品总数量和实付款
        total_count = 0
        total_amount = Decimal(0)

        # 订单状态
        # if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH']:
        #     # 货到付款
        #     status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] # 待发货
        # else:
        #     # 在线支付
        #     status = OrderInfo.ORDER_STATUS_ENUM['UNPAID'] # 待支付

        status = OrderInfo.ORDER_STATUS_ENUM['UNSEND'] if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH'] else OrderInfo.ORDER_STATUS_ENUM['UNPAID']

        # 获取redis链接
        redis_conn = get_redis_connection('cart')

        # 从redis中获取用户所要购买的商品sku_id  set
        cart_selected_key = 'cart_selected_%s' % user.id
        # (b'<sku_id>', ...)
        sku_ids = redis_conn.smembers(cart_selected_key)

        # 从redis中获取用户购物车商品的sku_id和对应的数量count  hash
        cart_key = 'cart_%s' % user.id
        # {
        #     b'<sku_id>': b'<count>',
        #     ...
        # }
        cart_dict = redis_conn.hgetall(cart_key)

        with transaction.atomic():
            # 在with语句块中代码，凡是涉及到数据库操作的代码，都会放到同一个事务中

            # 设置一个事务保存点
            sid = transaction.savepoint()

            try:
                # 1）向订单基本信息表添加一条记录
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=total_count,
                    total_amount=total_amount,
                    freight=freight,
                    pay_method=pay_method,
                    status=status
                )

                # 2）订单中包含几个商品，就需要向订单商品表中添加几条记录
                for sku_id in sku_ids:
                    # 获取用户所要购买的该商品的数量count
                    count = cart_dict[sku_id]
                    count = int(count)

                    # 根据sku_id获取商品信息
                    # select * from tb_sku where id=<sku_id>;
                    # sku = SKU.objects.get(id=sku_id)

                    # select * from tb_sku where id=<sku_id> for update;
                    print('user: %s try get lock' % user.id)
                    sku = SKU.objects.select_for_update().get(id=sku_id)
                    print('user: %s get locked' % user.id)

                    # 判断商品库存是否充足
                    if count > sku.stock:
                        # 回滚到sid事务保存点
                        transaction.savepoint_rollback(sid)
                        raise serializers.ValidationError('商品库存不足')

                    # 模拟订单并发问题
                    # print('user: %d' % user.id)
                    import time
                    time.sleep(10)

                    # 减少商品库存，增加销量
                    sku.stock -= count
                    sku.sales += count
                    sku.save()

                    # 向订单商品表中添加一条记录
                    OrderGoods.objects.create(
                        order=order,
                        sku=sku,
                        count=count,
                        price=sku.price
                    )

                    # 累加计算订单中商品总数量和总金额
                    total_count += count
                    total_amount += sku.price*count

                # 实付款
                total_amount += freight
                # 更新订单记录中商品的总数量和实付款
                order.total_count = total_count
                order.total_amount = total_amount
                order.save()
            except serializers.ValidationError:
                # 继续向外抛出异常
                raise
            except Exception as e:
                # 回滚sid事务保存点
                transaction.savepoint_rollback(sid)
                raise serializers.ValidationError('下单失败1')

        # 3）清除购物车中对应的记录
        pl = redis_conn.pipeline()
        pl.hdel(cart_key, *sku_ids)
        pl.srem(cart_selected_key, *sku_ids)
        pl.execute()

        # 返回订单对象
        return order
