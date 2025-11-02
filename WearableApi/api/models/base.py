"""
Base Models
===========
Abstract base models that other models inherit from.

Design Pattern: Template Method Pattern
Provides common structure and behavior for all models.
"""

from django.db import models # type: ignore


class TimeStampedModel(models.Model):
    """
    Abstract base model with automatic timestamp tracking.
    
    All models inheriting from this will have:
    - created_at: Auto-set on creation
    - updated_at: Auto-updated on every save
    
    Note: PostgreSQL triggers handle updated_at in the database,
    but Django also manages it for consistency.
    """
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the record was last updated"
    )
    
    class Meta:
        abstract = True  # This model will not create a database table
        ordering = ['-created_at']  # Default ordering by newest first
    
    def __str__(self):
        return f"{self.__class__.__name__} (ID: {self.pk})"


class SoftDeleteModel(TimeStampedModel):
    """
    Abstract model with soft delete functionality.
    
    Instead of deleting records, marks them as deleted.
    Useful for audit trails and data recovery.
    
    Usage:
        class MyModel(SoftDeleteModel):
            name = models.CharField(max_length=100)
        
        # Soft delete
        obj.delete()  # Sets is_deleted=True
        
        # Get active objects only
        MyModel.objects.active()
        
        # Get deleted objects
        MyModel.objects.deleted()
        
        # Get all (including deleted)
        MyModel.objects.all_with_deleted()
    """
    
    is_deleted = models.BooleanField(
        default=False,
        help_text="Flag indicating if record is soft-deleted"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when record was soft-deleted"
    )
    
    class Meta:
        abstract = True
    
    def delete(self, using=None, keep_parents=False):
        """Override delete to implement soft delete"""
        from django.utils import timezone # type: ignore
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(using=using)
    
    def hard_delete(self):
        """Permanently delete the record"""
        super().delete()
    
    def restore(self):
        """Restore a soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class SoftDeleteManager(models.Manager):
    """
    Custom manager for SoftDeleteModel.
    
    Provides convenient methods to filter by deletion status.
    """
    
    def get_queryset(self):
        """Default queryset excludes soft-deleted records"""
        return super().get_queryset().filter(is_deleted=False)
    
    def active(self):
        """Get only active (not deleted) records"""
        return self.get_queryset()
    
    def deleted(self):
        """Get only deleted records"""
        return super().get_queryset().filter(is_deleted=True)
    
    def all_with_deleted(self):
        """Get all records including deleted"""
        return super().get_queryset()