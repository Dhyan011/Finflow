from uuid import uuid4

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Account(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        CLOSED = "CLOSED", "Closed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="accounts",
    )
    account_number = models.CharField(max_length=20, unique=True)
    balance = models.DecimalField(max_digits=19, decimal_places=4, default=0)
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs) -> None:
        if not self.account_number:
            self.account_number = f"ACC{uuid4().hex[:12].upper()}"
        super().save(*args, **kwargs)
