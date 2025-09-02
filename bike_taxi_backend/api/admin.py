from django.contrib import admin
from .models import UserProfile, Vehicle, Ride, RideLocation, Payment


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone", "rating", "total_rides", "is_available", "created_at")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("driver", "plate_number", "make", "model")


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("id", "rider", "driver", "status", "estimated_fare", "created_at")
    list_filter = ("status",)


@admin.register(RideLocation)
class RideLocationAdmin(admin.ModelAdmin):
    list_display = ("ride", "lat", "lng", "pinged_at")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("ride", "amount", "currency", "status", "provider_ref")
