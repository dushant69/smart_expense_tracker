import csv
import io
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from .models import Expense, Budget
from .forms import ExpenseForm, SignUpForm, BudgetForm, ImportForm
from .ai import categorize_expense


def _month_total(user, year, month):
    """Total a user spent in a given month (helper)."""
    return (
        Expense.objects.filter(user=user, date__year=year, date__month=month)
        .aggregate(total=Sum('amount'))['total'] or Decimal('0')
    )


def signup(request):
    """Register a new user, then log them in automatically."""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully. Welcome!')
            return redirect('dashboard')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


@login_required
def dashboard(request):
    """Show the logged-in user's expenses plus totals and a category breakdown."""
    expenses = Expense.objects.filter(user=request.user)

    # Grand total of all the user's expenses.
    total = expenses.aggregate(total=Sum('amount'))['total'] or 0

    # Spending grouped by category, highest first.
    by_category = list(
        expenses.values('category')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    # Attach a colour to each category row (for the list + chart).
    for row in by_category:
        row['color'] = Expense.CATEGORY_COLORS.get(row['category'], '#64748b')

    # Data for the Chart.js doughnut chart.
    chart_data = {
        'labels': [row['category'] for row in by_category],
        'data': [float(row['total']) for row in by_category],
        'colors': [row['color'] for row in by_category],
    }

    # The single biggest category (for a stat card).
    top_category = by_category[0]['category'] if by_category else '—'

    # ----- Budget + monthly summary -----
    today = timezone.localdate()
    budget_obj = Budget.objects.filter(user=request.user).first()
    budget_amount = budget_obj.amount if budget_obj else Decimal('0')

    this_month_spent = _month_total(request.user, today.year, today.month)

    # Percentage of budget used this month (capped at 100 for the bar width).
    if budget_amount > 0:
        used_pct = min(float(this_month_spent) / float(budget_amount) * 100, 100)
        over_budget = this_month_spent > budget_amount
        remaining = budget_amount - this_month_spent
        over_amount = this_month_spent - budget_amount if over_budget else Decimal('0')
    else:
        used_pct, over_budget, remaining, over_amount = 0, False, Decimal('0'), Decimal('0')

    # Last month figures (for the "saved vs over" card).
    first_of_this_month = today.replace(day=1)
    last_month_day = first_of_this_month - timedelta(days=1)
    last_month_spent = _month_total(request.user, last_month_day.year, last_month_day.month)
    if budget_amount > 0:
        last_month_diff = budget_amount - last_month_spent  # +saved / -over
    else:
        last_month_diff = None

    context = {
        'expenses': expenses[:8],       # show the latest 8 on the dashboard
        'total': total,
        'by_category': by_category,
        'count': expenses.count(),
        'top_category': top_category,
        'chart_data': json.dumps(chart_data),
        # budget block
        'budget_amount': budget_amount,
        'this_month_spent': this_month_spent,
        'used_pct': round(used_pct),
        'over_budget': over_budget,
        'remaining': remaining,
        'over_amount': over_amount,
        'last_month_spent': last_month_spent,
        'last_month_diff': last_month_diff,
        'last_month_name': last_month_day.strftime('%B'),
    }
    return render(request, 'expenses/dashboard.html', context)


@login_required
def add_expense(request):
    """Create a new expense for the current user."""
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user  # attach the logged-in user
            expense.save()
            messages.success(request, 'Expense added.')
            return redirect('dashboard')
    else:
        form = ExpenseForm()
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Add Expense'})


@login_required
def edit_expense(request, pk):
    """Edit an existing expense (only if it belongs to the current user)."""
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Expense updated.')
            return redirect('dashboard')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'expenses/expense_form.html', {'form': form, 'title': 'Edit Expense'})


@login_required
def download_pdf(request):
    """Generate and download a PDF report of the user's expenses."""
    expenses = Expense.objects.filter(user=request.user)
    total = expenses.aggregate(total=Sum('amount'))['total'] or 0

    # Tell the browser to download this response as a PDF file.
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="expense_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title + small info line.
    elements.append(Paragraph("Expense Report", styles['Title']))
    elements.append(Paragraph(
        f"User: {request.user.username} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Generated on: {date.today().strftime('%d %b %Y')}",
        styles['Normal']))
    elements.append(Spacer(1, 0.6 * cm))

    # Build the table: header row + one row per expense.
    data = [['#', 'Title', 'Category', 'Date', 'Amount (Rs)']]
    for i, e in enumerate(expenses, start=1):
        data.append([str(i), e.title, e.category,
                     e.date.strftime('%d-%m-%Y'), f"{e.amount}"])
    # Final total row.
    data.append(['', '', '', 'TOTAL', f"{total}"])

    table = Table(data, colWidths=[1.2 * cm, 6 * cm, 3.5 * cm, 3 * cm, 3 * cm])
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f1f5f9')]),
        # Total row styling
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)

    doc.build(elements)
    return response


@login_required
def delete_expense(request, pk):
    """Delete an expense after a confirmation page."""
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted.')
        return redirect('dashboard')
    return render(request, 'expenses/expense_confirm_delete.html', {'expense': expense})


@login_required
def expenses_list(request):
    """Full expense list with search and category filter."""
    expenses = Expense.objects.filter(user=request.user)

    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()

    if query:
        expenses = expenses.filter(title__icontains=query)
    if category:
        expenses = expenses.filter(category=category)

    total = expenses.aggregate(total=Sum('amount'))['total'] or 0
    context = {
        'expenses': expenses,
        'total': total,
        'count': expenses.count(),
        'query': query,
        'selected_category': category,
        'categories': [c[0] for c in Expense.CATEGORY_CHOICES],
    }
    return render(request, 'expenses/expenses_list.html', context)


@login_required
def analytics(request):
    """Analytics page — charts that update by time range (handled in JS)."""
    return render(request, 'expenses/analytics.html')


@login_required
def analytics_data(request):
    """JSON endpoint powering the dynamic analytics charts.

    ?range=7|30|90  -> daily spending (line) + category totals (bar/pie)
    for that many days back.
    """
    try:
        days = int(request.GET.get('range', 30))
    except ValueError:
        days = 30
    if days not in (7, 30, 90, 180, 365):
        days = 30

    end = timezone.localdate()
    start = end - timedelta(days=days - 1)

    expenses = Expense.objects.filter(user=request.user, date__gte=start, date__lte=end)

    # --- Daily totals for the line chart ---
    # 'date' is already a DateField, so group on it directly.
    per_day = {
        row['date']: float(row['total'])
        for row in expenses.values('date').annotate(total=Sum('amount'))
    }
    line_labels, line_data = [], []
    for i in range(days):
        day = start + timedelta(days=i)
        line_labels.append(day.strftime('%d %b'))
        line_data.append(per_day.get(day, 0))

    # --- Category totals for the bar/pie chart ---
    cat_rows = (
        expenses.values('category').annotate(total=Sum('amount')).order_by('-total')
    )
    cat_labels = [r['category'] for r in cat_rows]
    cat_data = [float(r['total']) for r in cat_rows]
    cat_colors = [Expense.CATEGORY_COLORS.get(c, '#64748b') for c in cat_labels]

    total = float(expenses.aggregate(total=Sum('amount'))['total'] or 0)

    return JsonResponse({
        'range': days,
        'total': total,
        'line': {'labels': line_labels, 'data': line_data},
        'category': {'labels': cat_labels, 'data': cat_data, 'colors': cat_colors},
    })


@login_required
def budget_view(request):
    """Set or update the user's monthly budget."""
    budget_obj = Budget.objects.filter(user=request.user).first()
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget_obj)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            messages.success(request, 'Budget saved.')
            return redirect('dashboard')
    else:
        form = BudgetForm(instance=budget_obj)

    today = timezone.localdate()
    context = {
        'form': form,
        'current_budget': budget_obj.amount if budget_obj else None,
        'this_month_spent': _month_total(request.user, today.year, today.month),
    }
    return render(request, 'expenses/budget.html', context)


@login_required
def import_expenses(request):
    """Import expenses from an uploaded CSV, optionally AI-categorising each row.

    Expected CSV columns (header row): title, amount, date
    (date optional — defaults to today; category is decided by AI).
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            use_ai = form.cleaned_data['use_ai']
            f = form.cleaned_data['csv_file']
            try:
                decoded = f.read().decode('utf-8-sig')
            except UnicodeDecodeError:
                messages.error(request, 'Could not read file — please upload a UTF-8 CSV.')
                return redirect('import_expenses')

            reader = csv.DictReader(io.StringIO(decoded))
            created = 0
            for row in reader:
                # Accept flexible column names (case-insensitive).
                low = {k.lower().strip(): (v or '').strip() for k, v in row.items() if k}
                title = low.get('title') or low.get('description') or low.get('name')
                amount_raw = low.get('amount') or low.get('price')
                if not title or not amount_raw:
                    continue
                try:
                    amount = Decimal(amount_raw.replace(',', '').replace('₹', ''))
                except (InvalidOperation, AttributeError):
                    continue

                # Date: use the CSV value if present, else today.
                exp_date = date.today()
                raw_date = low.get('date')
                if raw_date:
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
                        try:
                            exp_date = datetime.strptime(raw_date, fmt).date()
                            break
                        except ValueError:
                            continue

                # Category: AI if asked and available, else use CSV or 'Other'.
                if use_ai:
                    category = categorize_expense(title)
                else:
                    category = (low.get('category') or 'Other').title()
                    if category not in [c[0] for c in Expense.CATEGORY_CHOICES]:
                        category = 'Other'

                Expense.objects.create(
                    user=request.user, title=title, amount=amount,
                    category=category, date=exp_date,
                )
                created += 1

            messages.success(request, f'Imported {created} expense(s).')
            return redirect('expenses_list')
    else:
        form = ImportForm()
    return render(request, 'expenses/import.html', {'form': form})


@login_required
def profile(request):
    """Simple profile page with the user's overall stats."""
    expenses = Expense.objects.filter(user=request.user)
    total = expenses.aggregate(total=Sum('amount'))['total'] or 0
    budget_obj = Budget.objects.filter(user=request.user).first()
    context = {
        'total': total,
        'count': expenses.count(),
        'budget': budget_obj.amount if budget_obj else None,
    }
    return render(request, 'expenses/profile.html', context)
