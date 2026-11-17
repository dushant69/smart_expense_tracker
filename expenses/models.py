from django.db import models
from django.contrib.auth.models import User


class Expense(models.Model):
    """A single expense entry that belongs to one user."""

    # Fixed set of categories shown as a dropdown in the form.
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Transport', 'Transport'),
        ('Shopping', 'Shopping'),
        ('Bills', 'Bills'),
        ('Entertainment', 'Entertainment'),
        ('Health', 'Health'),
        ('Other', 'Other'),
    ]

    # Each expense is linked to the logged-in user who created it.
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    title = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='Other',
    )
    date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # A colour for each category, reused in badges and the chart.
    CATEGORY_COLORS = {
        'Food': '#f97316',
        'Transport': '#3b82f6',
        'Shopping': '#ec4899',
        'Bills': '#ef4444',
        'Entertainment': '#8b5cf6',
        'Health': '#10b981',
        'Other': '#64748b',
    }

    class Meta:
        # Newest expenses first.
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.title} - ₹{self.amount}"

    @property
    def color(self):
        """Hex colour for this expense's category."""
        return self.CATEGORY_COLORS.get(self.category, '#64748b')


class Budget(models.Model):
    """The monthly spending limit a user sets for themselves."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='budget',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.username}'s budget: ₹{self.amount}"
