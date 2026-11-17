from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Sum, Count
from django.utils.html import format_html
from .models import Expense

# ---------------------------------------------------------------------------
# Branding (shows at the top of every admin page and on the login screen).
# ---------------------------------------------------------------------------
admin.site.site_header = "💰 Expense Tracker — Admin Panel"
admin.site.site_title = "Expense Tracker Admin"
admin.site.index_title = "Manage Expenses & Users"


# ---------------------------------------------------------------------------
# Expense admin
# ---------------------------------------------------------------------------
@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    # Columns shown in the list view.
    list_display = ('title', 'colored_amount', 'category', 'date', 'user', 'created_at')
    list_filter = ('category', 'date', 'user')            # right-side filter sidebar
    search_fields = ('title', 'notes', 'user__username')  # top search box
    date_hierarchy = 'date'                               # date drill-down bar
    ordering = ('-date',)
    list_per_page = 20
    list_editable = ('category',)                         # edit category inline
    readonly_fields = ('created_at',)

    fieldsets = (
        ('Expense Details', {
            'fields': ('user', 'title', 'amount', 'category', 'date')
        }),
        ('Extra', {
            'fields': ('notes', 'created_at'),
        }),
    )

    @admin.display(description='Amount', ordering='amount')
    def colored_amount(self, obj):
        return format_html('<b style="color:#198754;">₹{}</b>', obj.amount)

    def changelist_view(self, request, extra_context=None):
        """Show a grand total of the currently filtered expenses at the top."""
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            qs = response.context_data['cl'].queryset
            total = qs.aggregate(total=Sum('amount'))['total'] or 0
            response.context_data['title'] = f"Select expense to change — Total shown: ₹{total}"
        except (AttributeError, KeyError):
            pass
        return response


# ---------------------------------------------------------------------------
# Custom User admin: show how much EACH user has spent.
# ---------------------------------------------------------------------------
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Add two extra columns: number of expenses and total amount spent.
    list_display = (
        'username', 'email', 'expense_count', 'total_spent',
        'is_staff', 'is_superuser', 'date_joined',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active')

    def get_queryset(self, request):
        # Annotate each user with their expense count and total spend
        # so we can show and sort by them.
        qs = super().get_queryset(request)
        return qs.annotate(
            _expense_count=Count('expenses'),
            _total_spent=Sum('expenses__amount'),
        )

    @admin.display(description='Expenses', ordering='_expense_count')
    def expense_count(self, obj):
        return obj._expense_count

    @admin.display(description='Total Spent', ordering='_total_spent')
    def total_spent(self, obj):
        total = obj._total_spent or 0
        return format_html('<b style="color:#198754;">₹{}</b>', total)
