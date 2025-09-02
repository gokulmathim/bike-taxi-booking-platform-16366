from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile, Vehicle, Ride, RideLocation, Payment


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ["id", "user", "role", "phone", "rating", "total_rides", "is_available", "created_at", "updated_at"]


class VehicleSerializer(serializers.ModelSerializer):
    driver = UserSerializer(read_only=True)

    class Meta:
        model = Vehicle
        fields = ["id", "driver", "make", "model", "plate_number", "created_at", "updated_at"]


class RideLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RideLocation
        fields = ["id", "lat", "lng", "pinged_at", "created_at", "updated_at"]


class RideSerializer(serializers.ModelSerializer):
    rider = UserSerializer(read_only=True)
    driver = UserSerializer(read_only=True)
    locations = RideLocationSerializer(many=True, read_only=True)

    class Meta:
        model = Ride
        fields = [
            "id",
            "rider",
            "driver",
            "pickup_address",
            "dropoff_address",
            "pickup_lat",
            "pickup_lng",
            "dropoff_lat",
            "dropoff_lng",
            "status",
            "estimated_fare",
            "distance_km",
            "started_at",
            "completed_at",
            "locations",
            "created_at",
            "updated_at",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    ride = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Payment
        fields = ["id", "ride", "amount", "currency", "status", "provider_ref", "created_at", "updated_at"]


class RideCreateSerializer(serializers.Serializer):
    pickup_address = serializers.CharField()
    dropoff_address = serializers.CharField()
    pickup_lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    pickup_lng = serializers.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    dropoff_lng = serializers.DecimalField(max_digits=9, decimal_places=6)


class RideActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["match", "start", "complete", "cancel"])


class LocationPingSerializer(serializers.Serializer):
    lat = serializers.DecimalField(max_digits=9, decimal_places=6)
    lng = serializers.DecimalField(max_digits=9, decimal_places=6)
