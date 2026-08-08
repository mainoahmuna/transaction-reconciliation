from django.db import models

class Transaction(models.Model):
    source = models.CharField(max_length=20)  # "bank" or "ledger"
    external_id = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.source} - {self.external_id} ({self.amount})"

class ReconciliationRun(models.Model):
    STATUS_CHOICES = [("pending","Pending"),("processing","Processing"),
                       ("complete","Complete"),("failed","Failed")]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    source_file_key = models.CharField(max_length=255, blank=True)  # S3 key, added Phase 2

    def __str__(self):
        return f"Run {self.id} - {self.status}"

class Mismatch(models.Model):
    run = models.ForeignKey(ReconciliationRun, on_delete=models.CASCADE, related_name="mismatches")
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, null=True)
    reason = models.CharField(max_length=255)  # e.g. "amount mismatch", "missing in ledger"

    def __str__(self):
        return f"Mismatch in {self.run.id}: {self.reason}"
