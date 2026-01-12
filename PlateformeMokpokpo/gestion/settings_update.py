# À ajouter dans settings.py de votre projet Django

# Configuration de l'authentification
LOGIN_URL = 'management:login'
LOGIN_REDIRECT_URL = 'management:dashboard'
LOGOUT_REDIRECT_URL = 'management:login'

# Configuration des templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Ajoutez cette ligne
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
