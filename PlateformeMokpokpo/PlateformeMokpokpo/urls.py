from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView


urlpatterns = [
    path('admin/', admin.site.urls),
     # Authentification
    path('login/', LoginView.as_view(template_name='auth/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    
    path('', include('gestion.urls')),  # <- Ajouter les URLs de l'app
]
