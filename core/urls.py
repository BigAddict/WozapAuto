from django.urls import path

from .views import HomePageView, ComponentsDemoView, signup, signin, signout

urlpatterns = [
    path('', HomePageView.as_view(), name='home'),
    path('components-demo/', ComponentsDemoView.as_view(), name='components_demo'),
    path('signup/', signup, name='signup'),
    path('signin/', signin, name='signin'),
    path('signout/', signout, name='signout'),
]