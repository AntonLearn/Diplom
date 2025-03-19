from django.db import models
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator

STATE_CHOICES = (
    ('basket', 'Статус корзины'),
    ('new', 'Новый'),
    ('processing', 'Обрабатывается'),
    ('processed', 'Обработан'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен')
)

USER_TYPE_CHOICES = (
    ('Retailer', 'Продавец'),
    ('Client', 'Клиент')
)


class UserManager(BaseUserManager):
    use_in_migrations = True
    """
    Модель для управления пользователями UserManager использует email 
    в качестве уникального идентификатора при аутентификации
    """
    def create_user(self, email, password, **extra_fields):
        """
        Метод создает и сохраняет user с email и паролем
        """
        if not email:
            raise ValueError(_('The Email must be specified'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Метод создает и сохраняет superuser с email и паролем
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Модель для создания пользователя user с основной информацией о пользователе,
    используется email в качестве имени пользователя
    """
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    email = models.EmailField(_('Email'), unique=True)
    company = models.CharField(verbose_name='Компания', max_length=40, blank=True)
    position = models.CharField(verbose_name='Должность', max_length=40, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only'),
        validators=[username_validator],
        error_messages={
            'unique': _("User is not unique"),
        },
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Instead of deleting the account, you can simply unselect this check'
        ),
    )
    type = models.CharField(verbose_name='Тип пользователя', choices=USER_TYPE_CHOICES, max_length=8, default='Client')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)

    def __str__(self):
        return f'Name [{self.first_name} {self.last_name}], email [{self.email}]'


class Retailer(models.Model):
    """
    Модель продавец Retailer:
    - наименование продавца
    - URL сайта продавца
    - связь с моделью пользователя User
    - принимает или нет заказы продавец
    """
    name = models.CharField(max_length=50, verbose_name='Наименование продавца')
    url = models.URLField(verbose_name='Ссылка на сайт', null=True, blank=True)
    user = models.OneToOneField(User, verbose_name='Пользователь', on_delete=models.CASCADE)
    state = models.BooleanField(verbose_name='Статус получения заказов', default=True)

    class Meta:
        verbose_name = 'Продавцы'
        verbose_name_plural = "Список продавцов"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Category(models.Model):
    """
    Модель категорий товаров Category:
    - наименование категории товаров
    - связь с моделями продавцов Retailer
    """
    name = models.CharField(max_length=80, verbose_name='Наименование категории')
    retailers = models.ManyToManyField(Retailer, verbose_name='Продавцы', related_name='categories', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = "Список категорий"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Модель с базовой информацией о товарах Product:
    - наименование товара
    - связь с моделью категории Category
    """
    name = models.CharField(max_length=200, verbose_name='Наименование товара')
    category = models.ForeignKey(Category, verbose_name='Категория', related_name='products', blank=True,
                                 on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = "Список товаров"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    """
    Модель с основной информацией о товарах ProductInfo:
    - наименование блока информации о товаре
    - модель товара
    - каталожный номер товара
    - связь с моделью с базовой информацией о товаре Product
    - связь с моделью продавца Retailer
    - количество товара
    - цена отпускная единицы товара
    - цена рекомендуемая розничная товара
    """
    name = models.CharField(max_length=60, verbose_name='Наименование информации о товаре', blank=True)
    model = models.CharField(max_length=80, verbose_name='Модель', blank=True)
    cat_id = models.PositiveIntegerField(verbose_name='Каталожный номер')
    product = models.ForeignKey(Product, verbose_name='Товар', related_name='products_info', blank=True,
                                on_delete=models.CASCADE)
    retailer = models.ForeignKey(Retailer, verbose_name='Продавец', related_name='products_info', blank=True,
                                 on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.PositiveIntegerField(verbose_name='Цена')
    price_rrc = models.PositiveIntegerField(verbose_name='Розничная рекомендуемая цена')

    class Meta:
        verbose_name = 'Информация о товаре'
        verbose_name_plural = "Информация о товарах"
        constraints = [
            models.UniqueConstraint(fields=['product', 'retailer', 'cat_id'], name='unique_product_info'),
        ]

    def __str__(self):
        return f'{self.retailer.name}: {self.product.name}\n{self.price}: {self.price_rrc}'


class Parameter(models.Model):
    """
    Модель с наименованием произвольных характеристик товаров Parameter:
    - наименование характеристики товара
    """
    name = models.CharField(max_length=40, verbose_name='Название')

    class Meta:
        verbose_name = 'Наименование характеристики'
        verbose_name_plural = "Список наименований характеристик"
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    """
    Модель со значением произвольной характеристики товара:
    - связь с моделью, содержащей основную информацию о товарах ProductInfo
    - связь с моделью, описывающей наименования произвольной характеристики товара Parameter
    - значение параметра товара
    """
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о товаре',
                                     related_name='product_parameters', blank=True,
                                     on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр товара',
                                  related_name='product_parameters', blank=True,
                                  on_delete=models.CASCADE)
    value = models.CharField(verbose_name='Значение параметра', max_length=50)

    class Meta:
        verbose_name = 'Параметр товара'
        verbose_name_plural = "Список параметров товаров"
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter'),
        ]

    def __str__(self):
        return f'{self.product_info.model}: {self.parameter.name}'


class Contact(models.Model):
    """
    Модель с контактами пользователей Contact:
    - связь с моделью, содержащей основную информацию о пользователе
    - страна
    - регион
    - город
    - улица
    - дом
    - корпус
    - строение
    - квартира
    - телефон
    - почтовый индекс
    """
    user = models.ForeignKey(User, verbose_name='Пользователь',
                             related_name='contacts', blank=True,
                             on_delete=models.CASCADE)
    country = models.CharField(max_length=50, verbose_name='Страна')
    region = models.CharField(max_length=50, verbose_name='Регион', blank=True)
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=100, verbose_name='Улица')
    house = models.CharField(max_length=15, verbose_name='Дом')
    structure = models.CharField(max_length=15, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=15, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=15, verbose_name='Квартира', blank=True)
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    postal_code = models.CharField(max_length=10, verbose_name='Почтовый индекс')

    class Meta:
        verbose_name = 'Контакты пользователя'
        verbose_name_plural = "Список контактов пользователя"

    def __str__(self):
        return f'{self.user}\n{self.city}, {self.street}, {self.house}, {self.apartment}\n{self.phone}'


class Order(models.Model):
    """
    Модель с основной информацией о заказе Order:
    - связь с моделью, содержащей основную информацию о пользователе
    - дата заказа
    - статус заказа с выбором из списка STATE_CHOICES
    - связь с моделью содержащей контакты пользователя Contact
    """
    user = models.ForeignKey(User, verbose_name='Пользователь',
                             related_name='orders', blank=True,
                             on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    state = models.CharField(verbose_name='Статус', choices=STATE_CHOICES, max_length=15)
    contact = models.ForeignKey(Contact, verbose_name='Контакт',
                                blank=True, null=True,
                                on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = "Список заказов"
        ordering = ('-date',)

    def __str__(self):
        return f'{self.user}: {self.date}'


class OrderItem(models.Model):
    """
    Модель с описание позиций в заказе OrderItem:
    - связь с моделью, содержащей основную информацию о заказе Order
    - связь с моделью, содержащей основную информацию о товарах ProductInfo
    - количество товара в позиции заказа
    """
    order = models.ForeignKey(Order, verbose_name='Заказ',
                              related_name='ordered_items', blank=True,
                              on_delete=models.CASCADE)
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                   related_name='ordered_items', blank=True,
                                   on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = "Список позиций заказа"
        constraints = [
            models.UniqueConstraint(fields=['order', 'product_info'], name='unique_order_item'),
        ]


class ConfirmEmailToken(models.Model):
    class Meta:
        verbose_name = 'Токен подтверждения Email'
        verbose_name_plural = 'Токены подтверждения Email'

    @staticmethod
    def generate_key():
        """
        generates a pseudo random code using os.urandom and binascii.hexlify
        """
        return get_token_generator().generate_token()

    user = models.ForeignKey(User, related_name='confirm_email_tokens', on_delete=models.CASCADE,
                             verbose_name=_("The User which is associated to this password reset token"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Token creation date"))

    key = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return _("Password reset token for user {user}".format(user=self.user))
