from django.urls import path

from .views import HomePageView, signup, signin, signout, profile_view, profile_edit, profile_api

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('signup/', signup, name='signup'),
    path('signin/', signin, name='signin'),
    path('signout/', signout, name='signout'),
    path('profile/', profile_view, name='profile'),
    path('profile/edit/', profile_edit, name='profile_edit'),
    path('api/profile/', profile_api, name='profile_api'),
]