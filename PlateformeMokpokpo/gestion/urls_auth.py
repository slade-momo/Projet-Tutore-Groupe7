from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

# Au début du fichier urls.py du projet (dans myproject/urls.py)
path('login/', LoginView.as_view(template_name='auth/login.html', redirect_authenticated_user=True), name='login'),
path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
path('management/', include('app.urls')),  # Vos URLs de l'app
