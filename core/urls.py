from django.urls import path

from .views import (
    HomePageView, signup, signin, signout, profile_view, profile_edit, profile_api,
    forgot_password, password_reset_confirm, change_password
)

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('signup/', signup, name='signup'),
    path('signin/', signin, name='signin'),
    path('signout/', signout, name='signout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('profile/change-password/', change_password, name='change_password'),
    path('api/profile/', profile_api, name='profile_api'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/<str:uidb64>/<str:token>/', password_reset_confirm, name='password_reset_confirm'),
]