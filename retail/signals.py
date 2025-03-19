from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import Signal, receiver
from retail.models import ConfirmEmailToken, User


new_user_registered = Signal()

new_order = Signal()


@receiver(new_user_registered)
def new_user_registered_signal(user_id, **kwargs):
    """
    Отправляем письмо-сообщение на почту пользователя с токеном сброса пароля,
    полученным из объекта token_object
    Структура письма-сообщения:
    - информационный заголовок subject
    - токен body
    - адрес исходящей почты from_email
    - адрес почты пользователя to
    """
    token_object, created = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    message = EmailMultiAlternatives(
        subject=f"Password Reset Token for {token_object.user.email}",
        body=token_object.key,
        from_email=settings.EMAIL_HOST_USER,
        to=[token_object.user.email])
    message.send()


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    Отправляем письмо-сообщение на почту пользователя о готовности заказа
    Структура письма-сообщения:
    - информационный заголовок subject
    - токен body
    - адрес исходящей почты from_email
    - адрес почты пользователя to
    """
    user = User.objects.get(id=user_id)

    message = EmailMultiAlternatives(
        subject=f"Статус заказа изменен",
        body='Заказ готов',
        from_email=settings.EMAIL_HOST_USER,
        to=[user.email])
    message.send()
