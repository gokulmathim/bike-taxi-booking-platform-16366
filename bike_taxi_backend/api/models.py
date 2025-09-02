from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class UserProfile(TimeStampedModel):
    """Extended profile for users and drivers."""
    USER = "user"
    DRIVER = "driver"
    ROLE_CHOICES = [
        (USER, "User"),
        (DRIVER, "Driver"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=USER)
    phone = models.CharField(max_length=20, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_rides = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=False)  # applies for drivers

    def __str__(self) -> str:
        return f"{self.user.username} ({self.role})"


class Vehicle(TimeStampedModel):
    """Driver vehicle details."""
    driver = models.OneToOneField(User, on_delete=models.CASCADE, related_name="vehicle")
    make = models.CharField(max_length=64)
    model = models.CharField(max_length=64)
    plate_number = models.CharField(max_length=20, unique=True)

    def __str__(self) -> str:
        return f"{self.plate_number} - {self.make} {self.model}"


class Ride(TimeStampedModel):
    """Represents a bike taxi ride."""
    REQUESTED = "requested"
    MATCHED = "matched"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (REQUESTED, "Requested"),
        (MATCHED, "Matched"),
        (STARTED, "Started"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    ]

    rider = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rides")
    driver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="drives")
    pickup_address = models.CharField(max_length=255)
    dropoff_address = models.CharField(max_length=255)
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lat = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lng = models.DecimalField(max_digits=9, decimal_places=6)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=REQUESTED)
    estimated_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Ride #{self.pk} - {self.rider.username} -> {self.status}"


class RideLocation(TimeStampedModel):
    """Location pings for a ride to simulate tracking."""
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name="locations")
    lat = models.DecimalField(max_digits=9, decimal_places=6)
    lng = models.DecimalField(max_digits=9, decimal_places=6)
    pinged_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-pinged_at",)


class Payment(TimeStampedModel):
    """Payment record for rides."""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (PAID, "Paid"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
    ]

    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=8, default="USD")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    provider_ref = models.CharField(max_length=128, blank=True, default="")

    def __str__(self) -> str:
        return f"Payment #{self.pk} - {self.status} - {self.amount} {self.currency}"
