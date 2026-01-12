from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy


class CustomLoginView(LoginView):
    """Vue de connexion personnalisée"""
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard')


class CustomLogoutView(LogoutView):
    """Vue de déconnexion personnalisée"""
    next_page = reverse_lazy('login')
