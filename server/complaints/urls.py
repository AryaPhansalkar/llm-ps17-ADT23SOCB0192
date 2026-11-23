from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.HealthView.as_view(), name="health"),
    path("complaints/", views.ComplaintView.as_view(), name="complaints"),
]
