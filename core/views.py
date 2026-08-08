from rest_framework import viewsets
from .models import Transaction, ReconciliationRun, Mismatch
from .serializers import TransactionSerializer, ReconciliationRunSerializer, MismatchSerializer

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

class ReconciliationRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReconciliationRun.objects.all()
    serializer_class = ReconciliationRunSerializer

class MismatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Mismatch.objects.all()
    serializer_class = MismatchSerializer
