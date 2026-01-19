from django.shortcuts import render


def home(request):
    return render(request, 'internaute/index.html')

def produits(request):
    return render(request, 'internaute/produits.html')

def apropos(request):
    return render(request, 'internaute/apropos.html')

# Create your views here.
