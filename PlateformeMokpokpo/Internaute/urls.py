from django.urls import path
from .views import home, produits, apropos

urlpatterns = [
    path('', home, name='home'),
    path('catalogue/', produits, name='catalogue'),
    path('a-propos/', apropos, name='apropos'),
]
