from django.urls import path

from . import views

app_name = 'groups'

urlpatterns = [
    path('', views.my_groups, name='my_groups'),
    path('create/', views.create_group, name='create'),
    path('<uuid:group_id>/', views.group_detail, name='detail'),
    path('<uuid:group_id>/edit/', views.edit_group, name='edit'),
    path('<uuid:group_id>/archive/', views.archive_group, name='archive'),
    path('<uuid:group_id>/add-member/', views.add_member, name='add_member'),
    path('<uuid:group_id>/remove-member/<uuid:user_id>/', views.remove_member, name='remove_member'),
    path('<uuid:group_id>/delete/', views.delete_group, name='delete'),
]
