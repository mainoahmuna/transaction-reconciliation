from django.contrib import admin

from .models import Mismatch, ReconciliationRun, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("external_id", "source", "amount", "date")
    list_filter = ("source",)


@admin.register(ReconciliationRun)
class ReconciliationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "started_at", "completed_at", "source_file_key")


@admin.register(Mismatch)
class MismatchAdmin(admin.ModelAdmin):
    list_display = ("run", "transaction", "reason")
