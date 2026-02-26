from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView


urlpatterns = [
    path('admin/', admin.site.urls),
    # Authentification
    path('login/', LoginView.as_view(template_name='auth/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),

    # App gestion (espace privé — @login_required)
    path('gestion/', include('gestion.urls')),

    # App internaute (site vitrine public — à la racine)
    path('', include('Internaute.urls')),
]
