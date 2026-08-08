import uuid

from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Transaction, ReconciliationRun, Mismatch
from .serializers import TransactionSerializer, ReconciliationRunSerializer, MismatchSerializer
from .s3 import upload_file

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer

class ReconciliationRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReconciliationRun.objects.all()
    serializer_class = ReconciliationRunSerializer

class MismatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Mismatch.objects.all()
    serializer_class = MismatchSerializer

@api_view(["POST"])
def upload_file_view(request):
    file_obj = request.FILES.get("file")
    if file_obj is None:
        return Response(
            {"error": "No file provided (send it as multipart field 'file')"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    key = f"uploads/{uuid.uuid4().hex}/{file_obj.name}"
    upload_file(file_obj, key)

    run = ReconciliationRun.objects.create(source_file_key=key)
    return Response(
        ReconciliationRunSerializer(run).data,
        status=status.HTTP_201_CREATED,
    )
