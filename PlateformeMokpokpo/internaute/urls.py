from django.urls import path
from .views import home, produits, apropos

urlpatterns = [
    path('', home, name='home'),
    path('produits/', produits, name='produits'),
    path('apropos/', apropos, name='apropos'),
]
