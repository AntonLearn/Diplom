from django.urls import path
from django_rest_passwordreset.views import (reset_password_request_token,
                                             reset_password_confirm)
from retail.views import (PartnerUpdate, RegisterUser, LoginUser, LogoutUser, CategoryView,
                          RetailerView, ProductInfoView, BasketView, UserDetails,
                          ContactView, OrderView, PartnerState, PartnerOrders,
                          ConfirmUser)
from rest_framework.routers import DefaultRouter

r = DefaultRouter()
r.register(r'products', ProductInfoView, basename='retailers')

app_name = 'retail'
urlpatterns = r.urls
urlpatterns += [
    path('partner/update/', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state/', PartnerState.as_view(), name='partner-state'),
    path('partner/orders/', PartnerOrders.as_view(), name='partner-orders'),
    path('user/register/', RegisterUser.as_view(), name='user-register'),
    path('user/register/confirm/', ConfirmUser.as_view(), name='user-register-confirm'),
    path('user/details/', UserDetails.as_view(), name='user-details'),
    path('user/contact/', ContactView.as_view(), name='user-contact'),
    path('user/login/', LoginUser.as_view(), name='user-login'),
    path('user/logout/', LogoutUser.as_view(), name='user-logout'),
    path('user/password_reset/', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm/', reset_password_confirm, name='password-reset-confirm'),
    path('categories/', CategoryView.as_view(), name='categories'),
    path('retailers/', RetailerView.as_view(), name='retailers'),
    path('basket/', BasketView.as_view(), name='basket'),
    path('order/', OrderView.as_view(), name='order'),
]