import json
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from ujson import loads as load_json
from rest_framework.viewsets import ModelViewSet
from retail.models import (Retailer, Category, ProductInfo, Order,
                           OrderItem, Contact, ConfirmEmailToken)
from retail.serializers import (RegisterUserSerializer, UserDetailsSerializer,
                                CategoryViewSerializer, RetailerViewSerializer,
                                BasketViewSerializer, OrderItemSerializer,
                                ProductInfoViewSerializer, PartnerOrdersSerializer,
                                ContactViewSerializer, OrderViewSerializer)
from retail.tasks import send_email, get_import
from django_rest_passwordreset.signals import reset_password_token_created
from django.dispatch import receiver
from retail.models import STATE_CHOICES


def strtobool(logic_str: str) -> bool:
    logic_bool = True
    if logic_str.lower().strip() not in ['true', 'on', 'yes']:
        logic_bool = False
    return logic_bool


class RegisterUser(APIView):
    """
    Класс: регистрация клиентов-покупателей
    """
    def post(self, request, *args, **kwargs):
        if {'first_name', 'last_name', 'email', 'password'}.issubset(self.request.data):
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}},
                                    status=status.HTTP_403_FORBIDDEN)
            else:
                user_serializer = RegisterUserSerializer(data=request.data, partial=True)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    token, created = ConfirmEmailToken.objects.get_or_create(user_id=user.id)
                    send_email.delay('Confirmation of registration',
                                     f'Your confirmation token {token.key}',
                                     user.email)
                    return JsonResponse({'Status': True, 'Token for email confirmation': token.key},
                                        status=status.HTTP_201_CREATED)
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors},
                                        status=status.HTTP_403_FORBIDDEN)
        return JsonResponse({'Status': False, 'Errors': 'All necessary arguments are not specified'},
                            status=status.HTTP_400_BAD_REQUEST)


class ConfirmUser(APIView):
    """
    Класс: подтверждение почтового адреса
    """
    def post(self, request, *args, **kwargs):
        if {'email', 'token'}.issubset(request.data):
            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'The token or email is incorrectly specified'})
        return JsonResponse({'Status': False, 'Errors': 'All necessary arguments are not specified'})


class LoginUser(APIView):
    """
    Класс: авторизация пользователей
    """
    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'],
                                password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, created = Token.objects.get_or_create(user=user)
                    return JsonResponse({'Status': True, 'Token': token.key})
            return JsonResponse({'Status': False, 'Errors': 'Failed to authorize'},
                                status=status.HTTP_403_FORBIDDEN)
        return JsonResponse({'Status': False, 'Errors': 'All necessary arguments are not specified'},
                            status=status.HTTP_400_BAD_REQUEST)


class LogoutUser(APIView):
    """
    Класс: выход пользователей
    """
    def post(self, request, *args, **kwargs):
        user = request.user
        user_id = user.id
        if user is not None:
            if user.is_authenticated:
                Token.objects.filter(user=user).delete()
                return JsonResponse({'Status': True,
                                     'message': f'User {user_id}:[{user}] has successfully logged out'},
                                    status=status.HTTP_200_OK)
            return JsonResponse({'Status': False,
                                 'Errors': f'User {user_id}:[{user}] is not authenticated'},
                                status=status.HTTP_403_FORBIDDEN)
        return JsonResponse({'Status': False,
                             'Errors': 'Failed to authorize'}, status=status.HTTP_403_FORBIDDEN)


class UserDetails(APIView):
    """
    Класс: обработка данных пользователей
    """
    def get(self, request, *args, **kwargs):
        serializer = UserDetailsSerializer(request.user)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if {'password'}.issubset(request.data):
            if 'password' in request.data:
                try:
                    validate_password(request.data['password'])
                except Exception as password_error:
                    return JsonResponse({'Status': False, 'Errors': {'password': password_error}},
                                        status=status.HTTP_400_BAD_REQUEST)
            else:
                request.user.set_password(request.data['password'])
        user_serializer = UserDetailsSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True}, status=status.HTTP_200_OK)
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors},
                                status=status.HTTP_400_BAD_REQUEST)


class CategoryView(ListAPIView):
    """
    Класс: просмотр списка категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategoryViewSerializer


class RetailerView(ListAPIView):
    """
    Класс: просмотр списка продавцов
    """
    queryset = Retailer.objects.filter(state=True)
    serializer_class = RetailerViewSerializer


class ProductInfoView(ModelViewSet):
    """
    Класс: поиск товаров
    """
    serializer_class = ProductInfoViewSerializer
    http_method_names = ['get', ]

    def get_queryset(self):
        query = Q(retailer__state=True)
        retailer_id = self.request.query_params.get('retailer_id', None)
        category_id = self.request.query_params.get('category_id', None)
        if retailer_id is not None:
            query = query & Q(retailer_id=retailer_id)
        if category_id is not None:
            query = query & Q(product__category_id=category_id)
        queryset = ProductInfo.objects.filter(query).select_related(
            'retailer', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()
        return queryset


class BasketView(APIView):
    """
    Класс: обработка корзины
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        id_user = user.id
        basket = Order.objects.filter(user_id=id_user, state='basket').prefetch_related(
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
        serializer = BasketViewSerializer(basket, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        items = request.data.get('items')
        user = request.user
        id_user = user.id
        if items:
            try:
                items_dict = json.dumps(items)
            except ValueError as e:
                JsonResponse({'Status': False, 'Errors': f'Invalid request format {e}'})
            else:
                basket, created = Order.objects.get_or_create(user_id=id_user, state='basket')
                id_order = basket.id
                objects_created = 0
                for order_item in load_json(items_dict):
                    id_product_info = order_item.get('product_info', None)
                    if id_product_info is None:
                        return JsonResponse({'Status': False,
                                             'Errors': f'The required request parameter <product_info> is missing'},
                                            status=status.HTTP_400_BAD_REQUEST)
                    elif isinstance(id_product_info, int):
                        productinfo = ProductInfo.objects.filter(product_id=id_product_info).first()
                        if productinfo:
                            id_retailer = productinfo.retailer_id
                            quantity = order_item.get('quantity', None)
                            if quantity is None:
                                return JsonResponse({'Status': False,
                                                     'Errors': f'The required request parameter <quantity> is missing'},
                                                    status=status.HTTP_400_BAD_REQUEST)
                            if not quantity.is_integer():
                                return JsonResponse({'Status': False,
                                                     'Errors': f'Invalid type of request parameter <quantity>'},
                                                    status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return JsonResponse({'Status': False,
                                                 'Errors': f'Invalid value for <product_info> request parameter'},
                                                status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return JsonResponse({'Status': False,
                                             'Errors': f'Invalid type of request parameter <product_info>'},
                                            status=status.HTTP_400_BAD_REQUEST)
                    order_item.update({'order': id_order, 'retailer': id_retailer, 'state': 'basket'})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid(raise_exception=True):
                        try:
                            serializer.save()
                        except IntegrityError as e:
                            return JsonResponse({'Status': False, 'Errors': str(e)})
                        else:
                            objects_created += 1
                    else:
                        JsonResponse({'Status': False, 'Errors': serializer.errors})
                return JsonResponse({'Status': True,
                                     'Objects created': objects_created},
                                    status=status.HTTP_201_CREATED)
        return JsonResponse({'Status': False,
                             'Errors': 'All necessary arguments are not specified'},
                            status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        items = request.data.get('items')
        user = request.user
        id_user = user.id
        if items:
            try:
                items_dict = json.dumps(items)
            except ValueError as e:
                JsonResponse({'Status': False, 'Errors': f'Invalid request format {e}'})
            else:
                basket, created = Order.objects.get_or_create(user_id=id_user, state='basket')
                id_order = basket.id
                objects_updated = 0
                for order_item in json.loads(items_dict):
                    id_product_info = order_item.get('product_info', None)
                    if id_product_info is None:
                        return JsonResponse({'Status': False,
                                             'Errors': f'The required request parameter <product_info> is missing'},
                                            status=status.HTTP_400_BAD_REQUEST)
                    elif isinstance(id_product_info, int):
                        quantity = order_item.get('quantity', None)
                        if quantity is None:
                            return JsonResponse({'Status': False,
                                                 'Errors': f'The required request parameter <quantity> is missing'},
                                                status=status.HTTP_400_BAD_REQUEST)
                        if not quantity.is_integer():
                            return JsonResponse({'Status': False,
                                                 'Errors': f'Invalid type of request parameter <quantity>'},
                                                status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return JsonResponse({'Status': False,
                                             'Errors': f'Invalid type of request parameter <product_info>'},
                                            status=status.HTTP_400_BAD_REQUEST)
                    objects_updated += (OrderItem.objects.filter(order_id=id_order,
                                                                 product_info_id=id_product_info).
                                                          update(quantity=quantity))

                return JsonResponse({'Status': True,
                                     'Objects updated': objects_updated})

        return JsonResponse({'Status': False,
                             'Errors': 'All necessary arguments are not specified'},
                            status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        items_list = request.data.get('items')
        user = request.user
        id_user = user.id
        if items_list:
            basket, created = Order.objects.get_or_create(user_id=id_user, state='basket')
            query = Q()
            objects_deleted = False
            id_order = basket.id
            for order_item_id in items_list:
                if order_item_id.is_integer():
                    query_order_item = Q(order_id=id_order, id=order_item_id)
                    if OrderItem.objects.filter(query_order_item).exists():
                        query = query | query_order_item
                        objects_deleted = True
            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Objects deleted': deleted_count}, status=status.HTTP_200_OK)
        return JsonResponse({'Status': False, 'Error': 'All necessary arguments are not specified'},
                            status=status.HTTP_400_BAD_REQUEST)


class PartnerUpdate(APIView):
    """
    Класс: прайс-листа продавца
    """
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'},
                                status=status.HTTP_403_FORBIDDEN)
        if request.user.type != 'Retailer':
            return JsonResponse({'Status': False, 'Error': 'For retailers only'},
                                status=status.HTTP_403_FORBIDDEN)
        url = request.data.get('url')
        if url:
            try:
                task = get_import.delay(request.user.id, url)
            except IntegrityError as e:
                return JsonResponse({'Status': False,
                                     'Errors': f'Integrity Error: {e}'})
            return JsonResponse({'Status': True}, status=status.HTTP_200_OK)
        return JsonResponse({'Status': False,
                             'Errors': 'All necessary arguments are not specified'},
                            status=status.HTTP_400_BAD_REQUEST)


class PartnerState(APIView):
    """
    Класс: статус продавца
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        user_type = user.type
        if user_type != 'Retailer':
            return JsonResponse({'Status': False, 'Error': 'For retailers only'},
                                status=status.HTTP_403_FORBIDDEN)
        user_retailer = user.retailer
        serializer = RetailerViewSerializer(user_retailer)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        user = request.user
        user_type = user.type
        if user_type != 'Retailer':
            return JsonResponse({'Status': False, 'Error': 'For retailers only'},
                                status=status.HTTP_403_FORBIDDEN)
        data = request.data
        state = data.get('state')
        if state:
            state = strtobool(state)
            try:
                Retailer.objects.filter(user_id=request.user.id).update(state=state)
                return JsonResponse({'Status': True}, status=status.HTTP_200_OK)
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})
        return JsonResponse({'Status': False,
                             'Errors': 'All necessary arguments are not specified'})


class PartnerOrders(APIView):
    """
    Класс: получение заказов клиентов продавцом,
    изменение статуса заказа по мере продвижения заказа
    """
    def get(self, request, *args, **kwargs):
        state_choice_list = []
        for state_choice in STATE_CHOICES:
            state_choice_list.append(state_choice[0])
        user = request.user
        user_type = user.type
        id_user = user.id
        retailer_email = user.email
        if user_type != 'Retailer':
            return JsonResponse({'Status': False, 'Error': 'For retailers only'},
                                status=status.HTTP_403_FORBIDDEN)
        data = request.data
        state_order = data.get('state_order', None)
        query = Q(product_info__retailer__user_id=id_user)
        if state_order is None:
            query = query & Q(order__state='basket')
        elif isinstance(state_order, str):
            if state_order in state_choice_list:
                query = query & Q(order__state=state_order)
            elif state_order == 'all':
                query_choice = Q()
                for state_choice in state_choice_list:
                    query_choice = query_choice | Q(order__state=state_choice)
                query = query & query_choice
            else:
                return JsonResponse(
                    {'Status': False,
                     'error': "Invalid request parameter value <state_order>"},
                    status=status.HTTP_400_BAD_REQUEST)
        else:
            return JsonResponse({'Status': False,
                                 'error': "Invalid type request parameter <state_order>"},
                                status=status.HTTP_400_BAD_REQUEST)

        orderitems = (OrderItem.objects.filter(query).select_related('order').
                      prefetch_related('product_info__retailer__user__contacts',
                                       'product_info__product__category',
                                       'product_info__product_parameters__parameter').
                      select_related('order').distinct())
        serializer = PartnerOrdersSerializer(orderitems, many=True)
        data = serializer.data
        if data:
            send_email.delay('Order status update',
                             'The order(s) is(are) loaded', retailer_email)
            order_id_list = []
            query_order = Q()
            for item in data:
                order_in_item = item.get('order')
                order_id_in_item = order_in_item.get('id')
                if order_id_in_item not in order_id_list:
                    query_order = query_order | Q(id=order_id_in_item)
                    order_id_list.append(order_id_in_item)
            orders = Order.objects.filter(query_order)
            client_email_list = []
            for order in orders:
                client_email = order.user.email
                if client_email not in client_email_list:
                    client_email_list.append(client_email)
                    send_email.delay('Order status update',
                                     'The order(s) processing started', client_email)
        return Response(data)


class ContactView(APIView):
    """
    Класс: контакты покупателей
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        id_user = user.id
        contact = Contact.objects.filter(user_id=id_user)
        serializer = ContactViewSerializer(contact, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        user = request.user
        id_user = user.id
        data = request.data
        if {'country', 'city', 'street', 'house', 'phone', 'postal_code'}.issubset(request.data):
            request.POST._mutable = True
            request.data.update({'user': id_user})
            serializer = ContactViewSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True}, status=status.HTTP_201_CREATED)
            else:
                JsonResponse({'Status': False, 'Error': serializer.errors},
                             status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({'Status': False,
                             'Error': 'All necessary arguments are not specified'},
                            status=status.HTTP_401_UNAUTHORIZED)

    def put(self, request, *args, **kwargs):
        user = request.user
        id_user = user.id
        data = request.data
        if 'id_contact' in data:
            id_contact = data.get('id_contact', None)
            if id_contact is None:
                return JsonResponse({'Status': False,
                                     'Errors': f'The required request parameter <id_contact> is missing'},
                                    status=status.HTTP_400_BAD_REQUEST)
            elif not isinstance(id_contact, int):
                return JsonResponse({'Status': False,
                                     'Errors': f'Invalid type of request parameter <id_contact>'},
                                    status=status.HTTP_400_BAD_REQUEST)
            contact = Contact.objects.filter(id=id_contact, user_id=id_user).first()
            if not contact:
                return JsonResponse({'Status': False,
                                     'message': f"Contact [{id_contact}] is missing or "
                                                    f"does not belong to user [{id_user}]"},
                                        status=status.HTTP_400_BAD_REQUEST)
            serializer = ContactViewSerializer(contact, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({'Status': False, 'Error': serializer.errors},
                                    status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({'Status': False, 'Error': 'All necessary arguments are not specified'},
                            status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        user = request.user
        id_user = user.id
        ids_contact_list = request.data.get('ids_contact', None)
        if ids_contact_list is None:
            return JsonResponse({'Status': False,
                                 'Errors': f'The required request parameter <ids_contact> is missing'},
                                status=status.HTTP_400_BAD_REQUEST)
        elif not isinstance(ids_contact_list, list):
            return JsonResponse({'Status': False,
                             'Errors': f'Invalid type of request parameter <ids_contact>'},
                            status=status.HTTP_400_BAD_REQUEST)
        if ids_contact_list:
            id_contact_number = len(ids_contact_list)
            id_contact_no_deleted_list = []
            id_contact_deleted_list = []
            for id_contact in ids_contact_list:
                if not isinstance(id_contact, int):
                    return JsonResponse({'Status': False,
                                         'Error': "Invalid type in list of contacts"},
                                        status=status.HTTP_400_BAD_REQUEST)
                contact = Contact.objects.filter(id=id_contact, user_id=id_user).first()
                if contact is None:
                    id_contact_no_deleted_list.append(id_contact)
                else:
                    id_contact_deleted_list.append(id_contact)
                    contact.delete()
            id_contact_deleted_count = len(id_contact_deleted_list)
            if id_contact_deleted_count == id_contact_number:
                return JsonResponse({'Status': True, 'Object(s) deleted': id_contact_number},
                                    status=status.HTTP_200_OK)
            elif id_contact_deleted_count == 0:
                return JsonResponse({'Status': False,
                                     'error': f"Contact(All contacts) is(are) missing or "
                                              f"does(do) not belong to user [{id_user}]"},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                return JsonResponse({'Status': True,
                                    'message': f"Object(s) deleted': "
                                               f"{id_contact_deleted_count} of {id_contact_number}. "
                                               f"Contact(s) {id_contact_deleted_list} is(are) deleted successfully. "
                                               f"Contact(s) {id_contact_no_deleted_list} is(are) missing or "
                                               f"does(do) not belong to user [{id_user}]"},
                                    status=status.HTTP_200_OK)
        return JsonResponse({'Status': False,
                             'Error': 'All necessary arguments are not specified'},
                            status=status.HTTP_400_BAD_REQUEST)


class OrderView(APIView):
    """
    Класс: получение и размешение заказа покупателя
    """
    def get(self, request, *args, **kwargs):
        user = request.user
        id_user = user.id
        data = request.data
        if 'id_order' in data:
            id_order = data.get('id_order')
            if isinstance(id_order, str):
                if id_order == 'all':
                    order = (Order.objects.filter(user_id=id_user).exclude(state='basket').
                             prefetch_related('ordered_items__product_info__product__category',
                                              'ordered_items__product_info__product_parameters__parameter').
                             select_related('contact').annotate(total_sum=Sum(F('ordered_items__quantity')
                                                                              * F('ordered_items__product_info__price'))).
                             distinct().order_by('-date'))
                else:
                    return JsonResponse({'Status': False,
                                         'error': "Invalid value <id_order> request parameter"},
                                        status=status.HTTP_400_BAD_REQUEST)
            elif isinstance(id_order, int):
                if Order.objects.filter(user_id=id_user, id=id_order).exclude(state='basket').exists():
                    order = (Order.objects.filter(user_id=id_user, id=id_order).exclude(state='basket').
                             prefetch_related('ordered_items__product_info__product__category',
                                              'ordered_items__product_info__product_parameters__parameter').
                             select_related('contact').annotate(total_sum=Sum(F('ordered_items__quantity')
                                                                              * F('ordered_items__product_info__price'))).
                             distinct().order_by('-date'))
                else:
                    return JsonResponse({'Status': False,
                                         'error': f"Order [{id_order}] is missing or does not belong to user [{user}]"},
                                        status=status.HTTP_400_BAD_REQUEST)
            else:
                return JsonResponse({'Status': False,
                                     'error': "Invalid type <id_order> request parameter"},
                                    status=status.HTTP_400_BAD_REQUEST)
        else:
             return JsonResponse({'Status': False,
                                  'Error': 'All necessary arguments are not specified'},
                                 status=status.HTTP_400_BAD_REQUEST)
        serializer = OrderViewSerializer(order, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        data = request.data
        if {'order_id', 'contact_id'}.issubset(data):
            user = request.user
            id_user = user.id
            user_email = user.email
            id_order = data.get('order_id')
            if id_order is None:
                return JsonResponse({'Status': False,
                                     'Errors': f'The required request parameter <order_id> is missing'},
                                    status=status.HTTP_400_BAD_REQUEST)
            elif isinstance(id_order, int):
                id_contact = data.get('contact_id', None)
                if id_contact is None:
                    return JsonResponse({'Status': False,
                                         'Errors': f'The required request parameter <contact_id> is missing'},
                                        status=status.HTTP_400_BAD_REQUEST)
                if not id_contact.is_integer():
                    return JsonResponse({'Status': False,
                                         'Errors': f'Invalid type of request parameter <contact_id>'},
                                        status=status.HTTP_400_BAD_REQUEST)
            else:
                return JsonResponse({'Status': False,
                                     'Errors': f'Invalid type of request parameter <order_id>'},
                                    status=status.HTTP_400_BAD_REQUEST)
            if not Contact.objects.filter(user_id=id_user, id=id_contact).exists():
                return JsonResponse({'Status': False,
                                     'message': f"Contact [{id_contact}] is missing or "
                                                f"does not belong to user [{user}]"},
                                    status=status.HTTP_400_BAD_REQUEST)
            if not Order.objects.filter(user_id=id_user, id=id_order).exists():
                return JsonResponse({'Status': False,
                                     'message': f"Order [{id_order}] is missing or "
                                                f"does not belong to user [{user}]"},
                                    status=status.HTTP_400_BAD_REQUEST)
            is_updated = (Order.objects.filter(user_id=id_user, id=id_order).
                                        update(contact_id=id_contact, state='new'))
            if is_updated:
                send_email.delay('Order status update',
                                 f'The basket has been processed. '
                                 f'The order [{id_order}] has been formed',
                                 user_email)
                return JsonResponse({'Status': True}, status=status.HTTP_200_OK)
        return JsonResponse({'Status': False,
                             'Errors': 'All necessary arguments are not specified'},
                            status=status.HTTP_400_BAD_REQUEST)


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Отправка письма-сообщения с токеном для сброса пароля
    """
    send_email.delay(f"Password Reset Token for {reset_password_token.user}",
                     reset_password_token.key,
                     reset_password_token.user.email)
