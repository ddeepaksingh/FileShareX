from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    # My Files listing
    path('', views.my_files, name='my_files'),

    # Upload
    path('upload/', views.upload_page, name='upload'),
    path('upload/chunk/', views.receive_chunk, name='upload_chunk'),
    path('upload/finalize/', views.finalize_upload, name='upload_finalize'),

    # File detail & download
    path('<uuid:file_id>/', views.file_detail, name='detail'),
    path('<uuid:file_id>/download/', views.file_download, name='download'),

    # Folder
    path('folder/create/', views.create_folder, name='create_folder'),

    # Trash
    path('trash/', views.trash, name='trash'),
    path('<uuid:file_id>/delete/', views.delete_file, name='delete'),
    path('<uuid:file_id>/restore/', views.restore_file, name='restore'),
    path('<uuid:file_id>/destroy/', views.destroy_file, name='destroy'),
    path('trash/empty/', views.empty_trash, name='empty_trash'),
]
