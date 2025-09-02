from datetime import datetime
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import UserProfile, Vehicle, Ride, RideLocation, Payment
from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    VehicleSerializer,
    RideSerializer,
    RideCreateSerializer,
    RideActionSerializer,
    LocationPingSerializer,
    PaymentSerializer,
)
from .services import haversine, estimate_fare_km, match_nearest_available_driver


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health(request):
    """Simple health check endpoint."""
    return Response({"message": "Server is up!"})


class IsDriver(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and hasattr(request.user, "profile") and request.user.profile.role == UserProfile.DRIVER)


class IsAuthenticatedOrReadOnly(permissions.IsAuthenticatedOrReadOnly):
    pass


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    # PUBLIC_INTERFACE
    @swagger_auto_schema(method="post", operation_id="auth_register", operation_description="Register a new user or driver.")
    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        """
        Register a new user.

        Body:
        - username, password, email (optional), role ["user"|"driver"], phone (optional)

        Returns:
        - user and profile details
        """
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email", "")
        role = request.data.get("role", UserProfile.USER)
        phone = request.data.get("phone", "")

        if not username or not password:
            return Response({"detail": "username and password required"}, status=status.HTTP_400_BAD_REQUEST)
        if role not in [UserProfile.USER, UserProfile.DRIVER]:
            return Response({"detail": "invalid role"}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({"detail": "username already exists"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = User.objects.create_user(username=username, password=password, email=email)
            profile = UserProfile.objects.create(user=user, role=role, phone=phone, is_available=(role == UserProfile.DRIVER))
        return Response({"user": UserSerializer(user).data, "profile": UserProfileSerializer(profile).data}, status=201)

    # PUBLIC_INTERFACE
    @swagger_auto_schema(method="post", operation_id="auth_login", operation_description="Authenticate a user and return basic info.")
    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        """
        Login endpoint (session-based for simplicity).

        Body:
        - username, password

        Returns:
        - user info if authenticated
        """
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if not user:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response({"user": UserSerializer(user).data, "profile": UserProfileSerializer(user.profile).data})

    # PUBLIC_INTERFACE
    @swagger_auto_schema(method="get", operation_id="auth_me", operation_description="Get current user and profile.")
    @action(detail=False, methods=["get"], url_path="me", permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Return current user and profile."""
        return Response({"user": UserSerializer(request.user).data, "profile": UserProfileSerializer(request.user.profile).data})


class ProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only user profiles."""
    queryset = UserProfile.objects.select_related("user").all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]


class VehicleViewSet(viewsets.ModelViewSet):
    """Drivers can manage their vehicle."""
    serializer_class = VehicleSerializer
    permission_classes = [permissions.IsAuthenticated, IsDriver]

    def get_queryset(self):
        return Vehicle.objects.filter(driver=self.request.user)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)


class RideViewSet(viewsets.ModelViewSet):
    """Manage rides: create, match, start, complete, cancel and track."""
    queryset = Ride.objects.select_related("rider", "driver").all()
    serializer_class = RideSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, "profile") and user.profile.role == UserProfile.DRIVER:
            return self.queryset.filter(driver=user)
        return self.queryset.filter(rider=user)

    # PUBLIC_INTERFACE
    @swagger_auto_schema(request_body=RideCreateSerializer, responses={201: RideSerializer})
    def create(self, request, *args, **kwargs):
        """Create a ride request and return estimated fare."""
        serializer = RideCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        distance = haversine(data["pickup_lat"], data["pickup_lng"], data["dropoff_lat"], data["dropoff_lng"])
        fare = estimate_fare_km(distance)

        ride = Ride.objects.create(
            rider=request.user,
            pickup_address=data["pickup_address"],
            dropoff_address=data["dropoff_address"],
            pickup_lat=data["pickup_lat"],
            pickup_lng=data["pickup_lng"],
            dropoff_lat=data["dropoff_lat"],
            dropoff_lng=data["dropoff_lng"],
            distance_km=distance,
            estimated_fare=fare.total,
        )
        return Response(RideSerializer(ride).data, status=status.HTTP_201_CREATED)

    # PUBLIC_INTERFACE
    @swagger_auto_schema(method="post", request_body=RideActionSerializer)
    @action(detail=True, methods=["post"], url_path="action")
    def action(self, request, pk=None):
        """Perform an action on a ride: match, start, complete, cancel."""
        ride = self.get_object()
        act = RideActionSerializer(data=request.data)
        act.is_valid(raise_exception=True)
        action_name = act.validated_data["action"]

        if action_name == "match":
            if ride.status != Ride.REQUESTED:
                return Response({"detail": "Ride not in requested state"}, status=400)
            driver = match_nearest_available_driver(ride.pickup_lat, ride.pickup_lng)
            if not driver:
                return Response({"detail": "No drivers available"}, status=409)
            ride.driver = driver
            ride.status = Ride.MATCHED
            ride.save(update_fields=["driver", "status", "updated_at"])
            return Response(RideSerializer(ride).data)

        if action_name == "start":
            if ride.status not in [Ride.MATCHED]:
                return Response({"detail": "Ride must be matched to start"}, status=400)
            if ride.driver != request.user:
                return Response({"detail": "Only assigned driver can start"}, status=403)
            ride.status = Ride.STARTED
            ride.started_at = timezone.now()
            ride.save(update_fields=["status", "started_at", "updated_at"])
            return Response(RideSerializer(ride).data)

        if action_name == "complete":
            if ride.status not in [Ride.STARTED]:
                return Response({"detail": "Ride must be started to complete"}, status=400)
            if ride.driver != request.user:
                return Response({"detail": "Only assigned driver can complete"}, status=403)
            ride.status = Ride.COMPLETED
            ride.completed_at = timezone.now()
            ride.save(update_fields=["status", "completed_at", "updated_at"])
            # create payment record if not exists
            Payment.objects.get_or_create(ride=ride, defaults={"amount": ride.estimated_fare, "currency": "USD"})
            # increment stats
            for u in [ride.rider, ride.driver]:
                if hasattr(u, "profile"):
                    u.profile.total_rides = (u.profile.total_rides or 0) + 1
                    u.profile.save(update_fields=["total_rides", "updated_at"])
            return Response(RideSerializer(ride).data)

        if action_name == "cancel":
            if ride.status in [Ride.COMPLETED, Ride.CANCELLED]:
                return Response({"detail": "Ride already finished"}, status=400)
            # both rider and driver can cancel if not completed
            ride.status = Ride.CANCELLED
            ride.save(update_fields=["status", "updated_at"])
            return Response(RideSerializer(ride).data)

        return Response({"detail": "Unknown action"}, status=400)

    # PUBLIC_INTERFACE
    @swagger_auto_schema(method="post", request_body=LocationPingSerializer, responses={200: RideSerializer})
    @action(detail=True, methods=["post"], url_path="ping", permission_classes=[permissions.IsAuthenticated, IsDriver])
    def ping(self, request, pk=None):
        """Drivers send location ping for ride tracking."""
        ride = self.get_object()
        if ride.driver != request.user:
            return Response({"detail": "Only assigned driver can ping"}, status=403)
        if ride.status not in [Ride.STARTED, Ride.MATCHED]:
            return Response({"detail": "Ride is not active"}, status=400)
        ser = LocationPingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        RideLocation.objects.create(ride=ride, lat=ser.validated_data["lat"], lng=ser.validated_data["lng"])
        ride.refresh_from_db()
        return Response(RideSerializer(ride).data)


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """List or retrieve payment records for user's rides."""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Payment.objects.filter(ride__rider=user) | Payment.objects.filter(ride__driver=user)

    # PUBLIC_INTERFACE
    @swagger_auto_schema(method="post", operation_description="Simulate payment capture for a ride.")
    @action(detail=True, methods=["post"], url_path="capture")
    def capture(self, request, pk=None):
        """Mark payment as paid with a fake provider reference."""
        payment = self.get_object()
        if payment.ride.rider != request.user and payment.ride.driver != request.user:
            return Response({"detail": "Forbidden"}, status=403)
        if payment.status == Payment.PAID:
            return Response({"detail": "Already paid"}, status=400)
        payment.status = Payment.PAID
        payment.provider_ref = f"SIM-{int(datetime.utcnow().timestamp())}"
        payment.save(update_fields=["status", "provider_ref", "updated_at"])
        return Response(PaymentSerializer(payment).data)
