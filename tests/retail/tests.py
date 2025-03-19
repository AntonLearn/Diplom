import pytest
from django.urls import reverse
from rest_framework.status import HTTP_200_OK, HTTP_401_UNAUTHORIZED, HTTP_201_CREATED, HTTP_403_FORBIDDEN

from retail.models import User

@pytest.mark.django_db
def test_user_create(api_client):
    some_user = {
        "first_name": "Tatyana",
        "last_name": "Tatyanina",
        "email": "tanyamyasnov1712@yandex.ru",
        "password": "client1password"
    }

    url = reverse("retail:user-register")
    resp = api_client.post(url, data=some_user, format='json')

    assert resp.status_code == HTTP_201_CREATED
    assert resp.json().get('Status') is True


@pytest.mark.django_db
def test_user_confirm(api_client, user_factory, confirm_email_token_factory):
    user = user_factory()
    tok = confirm_email_token_factory()
    user.confirm_email_tokens.add(tok)
    url = reverse("retail:user-register-confirm")
    resp = api_client.post(url, data={"email": user.email, "token": "wrong_key"})
    assert resp.status_code == HTTP_200_OK
    assert resp.json().get('Status') is False
    resp = api_client.post(url, data={"email": user.email, "token": tok.key})
    assert resp.status_code == HTTP_200_OK
    assert resp.json().get('Status') is True


@pytest.mark.django_db
def test_user_login(api_client, user_factory):
    mail = "test@gmail.com"
    passw = "cdjndcbdbcdh12345"

    some_user = {
        "first_name": "testfirstname",
        "last_name": "testlastname",
        "email": mail,
        "password": passw,
        "company": "Yandex",
        "position": "Specialist"
    }

    url = reverse("retail:user-register")
    resp = api_client.post(url, data=some_user)
    assert resp.json().get('Status') is True

    user = User.objects.get(email=mail)
    user.is_active = True
    user.save()

    url = reverse("retail:user-login")
    resp = api_client.post(url, data={"email": mail, "password": passw})
    assert resp.status_code == HTTP_200_OK
    assert resp.json().get('Status') is True


@pytest.mark.django_db
def test_user_details(api_client, user_factory):
    url = reverse("retail:user-details")
    user = user_factory()
    api_client.force_authenticate(user=user)
    resp = api_client.get(url)
    assert resp.status_code == HTTP_200_OK
    resp = api_client.post(url, data={
        "first_name": "Ivan",
        "last_name": "Ivanov",
        "company": "Retailer1",
        "position": "Manager1",
        "email": "antonlearn@yandex.ru",
        "password": "retailer1password",
        "type": "Retailer"
    })
    assert resp.status_code == HTTP_200_OK

@pytest.mark.django_db
def test_user_contacts(api_client, user_factory):
    url = reverse("retail:user-contact")
    user = user_factory()
    api_client.force_authenticate(user=user)
    contact = { "country": "Russia",
    "city": "Moscow",
    "street": "Red Square",
    "house": "1",
    "apartment": "1",
    "phone": "00-00-00",
    "postal_code": "100000"
                }

    resp = api_client.post(url, data=contact)
    assert resp.status_code == HTTP_201_CREATED
    data = api_client.get(url)
    assert data.json()[0].get('house') == "1"


@pytest.mark.django_db
def test_products(api_client, user_factory, retailer_factory, order_factory,
                product_info_factory, product_factory, category_factory):
    url = reverse("retail:retailers")
    retailer = retailer_factory()
    customer = user_factory()
    category = category_factory()
    prod = product_factory(category=category)
    prod_info = product_info_factory(product=prod, retailer=retailer)
    api_client.force_authenticate(user=customer)
    retailer_id = retailer.id
    category_id = category.id
    resp = api_client.get(url, retailer_id=retailer.id, category_id=category.id)
    assert resp.status_code == HTTP_200_OK
    assert resp.json().get('results')[0]['id'] == 1


@pytest.mark.django_db
def test_category_get(api_client, category_factory):
    url = reverse('retail:categories')
    category_factory(_quantity=4)
    response = api_client.get(url)
    assert response.status_code == 200
    assert len(response.data) == 4