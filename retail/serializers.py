from rest_framework import serializers
from retail.models import (Contact, User, Category, Retailer,
                           Product, ProductParameter, ProductInfo,
                           Order, OrderItem)


class ContactViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'country', 'region', 'city', 'street', 'house',
                  'structure', 'building', 'apartment', 'user', 'phone',
                  'postal_code')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


class UserSerializer(serializers.ModelSerializer):
    contacts = ContactViewSerializer(read_only=True, many=True)
    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'company',
                  'position', 'contacts', 'type')
        read_only_fields = ('id', )


class RegisterUserSerializer(UserSerializer):
    pass


class UserDetailsSerializer(UserSerializer):
    pass


class CategoryViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')
        read_only_fields = ('id', )


class RetailerViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Retailer
        fields = ('id', 'name', 'state')
        read_only_fields = ('id', )


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    class Meta:
        model = Product
        fields = ('name', 'category',)


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()
    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoViewSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)
    class Meta:
        model = ProductInfo
        fields = ('id', 'model', 'cat_id', 'product', 'retailer', 'quantity', 'price', 'price_rrc', 'product_parameters',)
        read_only_fields = ('id',)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'order')
        read_only_fields = ('id', )
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    product_info = ProductInfoViewSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)
    total_sum = serializers.IntegerField()
    contact = ContactViewSerializer(read_only=True)
    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'state', 'contact', 'total_sum')
        read_only_fields = ('id',)


class BasketViewSerializer(OrderSerializer):
    pass


class OrderViewSerializer(OrderSerializer):
    pass


class PartnerOrderSerializer(serializers.ModelSerializer):
    contact = ContactViewSerializer(read_only=True)
    class Meta:
        model = Order
        fields = ('id', 'state', 'contact')
        read_only_fields = ('id', )


class PartnerOrdersSerializer(serializers.ModelSerializer):
    order = PartnerOrderSerializer(read_only=True)
    product_info = ProductInfoViewSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = ('order', 'id', 'product_info', 'quantity')
        read_only_fields = ('id', )