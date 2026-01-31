from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('register/', views.register, name='register'),
    
    # Settings
    path('settings/', views.settings, name='settings'),
    
    # User Management (solo para admins)
    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_update, name='user_update'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('backups/', views.backup_list, name='backup_list'),
    path('backups/crear/', views.create_backup, name='create_backup'),
    path('backups/descargar/<str:filename>/', views.download_backup, name='download_backup'),
    path('backups/eliminar/<str:filename>/', views.delete_backup, name='delete_backup'),
    path('backups/limpiar/', views.clean_old_backups, name='clean_old_backups'),
    
    

]