from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import health, AuthViewSet, ProfileViewSet, VehicleViewSet, RideViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r"profiles", ProfileViewSet, basename="profiles")
router.register(r"vehicles", VehicleViewSet, basename="vehicles")
router.register(r"rides", RideViewSet, basename="rides")
router.register(r"payments", PaymentViewSet, basename="payments")

urlpatterns = [
    path("health/", health, name="Health"),
    path("", include(router.urls)),
]
