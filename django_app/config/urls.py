from django.urls import path
from app.api import api

urlpatterns = [
    path("", api.urls),
]
