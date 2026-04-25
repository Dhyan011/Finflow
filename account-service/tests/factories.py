from decimal import Decimal

import factory

from apps.accounts.models import Account
from apps.transactions.models import Transaction
from apps.users.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    full_name = factory.Faker("name")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")


class AccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Account

    user = factory.SubFactory(UserFactory)
    currency = "USD"
    status = Account.Status.ACTIVE


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Transaction

    account = factory.SubFactory(AccountFactory)
    amount = Decimal("100.00")
    direction = Transaction.Direction.CREDIT
    status = Transaction.Status.PENDING
