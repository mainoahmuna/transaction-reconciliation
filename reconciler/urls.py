from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import TransactionViewSet, ReconciliationRunViewSet, MismatchViewSet

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet)
router.register(r'runs', ReconciliationRunViewSet)
router.register(r'mismatches', MismatchViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
]
