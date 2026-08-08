from rest_framework import serializers
from .models import Transaction, ReconciliationRun, Mismatch

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

class ReconciliationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationRun
        fields = '__all__'

class MismatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mismatch
        fields = '__all__'
