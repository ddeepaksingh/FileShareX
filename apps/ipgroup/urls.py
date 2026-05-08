from django.urls import path
from . import views

app_name = 'ipgroup'

urlpatterns = [
    path('',                          views.ip_files,        name='ip_files'),
    path('upload/',                   views.ip_upload_page,  name='ip_upload'),
    path('<uuid:file_id>/',           views.ip_file_detail,  name='ip_file_detail'),
    path('<uuid:file_id>/download/',  views.ip_file_download, name='ip_file_download'),
    path('<uuid:file_id>/delete/',    views.ip_file_delete,  name='ip_file_delete'),
]
