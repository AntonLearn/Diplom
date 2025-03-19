import pytest
from rest_framework.test import APIClient
from model_bakery import baker


@pytest.fixture
def api_client():
    client = APIClient()
    return client


@pytest.fixture
def user_factory():
    def factory(**kwargs):
        return baker.make('retail.User', **kwargs)

    return factory


@pytest.fixture
def confirm_email_token_factory():
    def factory(**kwargs):
        return baker.make('retail.ConfirmEmailToken', **kwargs)

    return factory


@pytest.fixture
def retailer_factory():
    def factory(**kwargs):
        return baker.make('retail.Retailer', **kwargs)

    return factory


@pytest.fixture
def order_factory():
    def factory(**kwargs):
        return baker.make('retail.Order', **kwargs)

    return factory


@pytest.fixture
def order_item_factory():
    def factory(**kwargs):
        return baker.make('retail.OrderItem', **kwargs)

    return factory


@pytest.fixture
def product_info_factory():
    def factory(**kwargs):
        return baker.make('retail.ProductInfo', **kwargs)

    return factory


@pytest.fixture
def product_factory():
    def factory(**kwargs):
        return baker.make('retail.Product', **kwargs)

    return factory


@pytest.fixture
def category_factory():
    def factory(**kwargs):
        return baker.make('retail.Category', **kwargs)

    return factory


@pytest.fixture
def contact_factory():
    def factory(**kwargs):
        return baker.make('retail.Contact', **kwargs)

    return factory