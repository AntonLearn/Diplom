import requests
import yaml
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.db import IntegrityError


from retail.models import (Retailer, Category, Product, Parameter,
                           ProductParameter, ProductInfo)
from diplom.celery import celery_app


@celery_app.task()
def send_email(title, message, email, *args, **kwargs):
    email_list = list()
    email_list.append(email)
    try:
        msg = EmailMultiAlternatives(
            subject=title,
            body=message,
            from_email=settings.EMAIL_HOST_USER,
            to=email_list)
        msg.send()
        return f'{title}: {msg.subject}, Message:{msg.body}'
    except Exception as e:
        raise e


@celery_app.task()
def get_import(partner, url):
    print(f'{url=}, {partner=}')
    if url:
        validate_url = URLValidator()
        try:
            validate_url(url)
        except ValidationError as e:
            return {'Status': False, 'Error': str(e)}
        else:
            print(f'{url=}, {partner=}')
            stream_url = requests.get(url)
            print(f'{stream_url=}')
            stream=stream_url.content
            print(f'{stream=}')

        data = yaml.load(stream, Loader=yaml.Loader)
        print(f'{data=}')
        try:
            print(f'{data['retailer']=}')
            print(f'{partner=}')
            retailer, created = Retailer.objects.get_or_create(
                name=data['retailer'],
                user_id=partner)
        except IntegrityError as e:
            return {'Status': False, 'Error': str(e)}

        for category in data['categories']:
            category_object, created = Category.objects.get_or_create(
                id=category['id'],
                name=category['name'])
            category_object.retailers.add(retailer.id)
            category_object.save()

        ProductInfo.objects.filter(retailer_id=retailer.id).delete()
        for item in data['goods']:
            product, created = Product.objects.get_or_create(
                name=item['name'],
                category_id=item['category'])
            product_info = ProductInfo.objects.create(
                product_id=product.id, cat_id=item['id'],
                model=item['model'], price=item['price'],
                price_rrc=item['price_rrc'], quantity=item['quantity'],
                retailer_id=retailer.id)
            for name, value in item['parameters'].items():
                parameter_object, created = Parameter.objects.get_or_create(name=name)
                ProductParameter.objects.create(
                    product_info_id=product_info.id,
                    parameter_id=parameter_object.id,
                    value=value)
        return {'Status': True}
    return {'Status': False, 'Errors': 'Url is false'}
