
from django.urls import path

from . import views

from .views import admin_dashboard


urlpatterns = [

    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('student-login/', views.student_login, name='student_login'),
    path('report/', views.report_item, name='report_item'),
    path('items/', views.items, name='items'),
    path('search/', views.search_items, name='search_items'),
    path('claim/', views.submit_claim, name='submit_claim'),
    path('api/compare-claim-images/', views.compare_claim_images, name='compare_claim_images'),
    path('manage-claims/', views.manage_claims, name='manage_claims'),
    path('approve-claim/<int:claim_id>/', views.approve_claim, name='approve_claim'),
    path('reject-claim/<int:claim_id>/', views.reject_claim, name='reject_claim'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.admin_logout, name='admin_logout'),
    path('student-dashboard/',views.student_dashboard,name='student_dashboard'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('view-students/', views.view_students, name='view_students'),
    path('view-all-items/',views.view_all_items,name='view_all_items'),
    path('update-item-status/<int:pk>/', views.update_item_status,name='update_item_status'),
    path(
    'edit-item-image/<int:item_id>/',
    views.edit_item_image,
    name='edit_item_image'
),
path('student-logout/', views.student_logout, name='logout'),
]
