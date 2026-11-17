from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add/', views.add_expense, name='add_expense'),
    path('edit/<int:pk>/', views.edit_expense, name='edit_expense'),
    path('delete/<int:pk>/', views.delete_expense, name='delete_expense'),
    path('download/pdf/', views.download_pdf, name='download_pdf'),
    path('expenses/', views.expenses_list, name='expenses_list'),
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/data/', views.analytics_data, name='analytics_data'),
    path('budget/', views.budget_view, name='budget'),
    path('import/', views.import_expenses, name='import_expenses'),
    path('profile/', views.profile, name='profile'),
    path('signup/', views.signup, name='signup'),
]
