from django.urls import path
from . import views
urlpatterns=[
    path("",views.homepage_view,name="Home"),
    path("signup/",views.register_view,name='signup'),
    path("forms/",views.forms_view,name='forms'),
    path("Test/",views.test_api),
    path("login/",views.login_view,name='login'),
    path("forms/save/", views.save_form, name="save_form"),
    path("forms/save/", views.save_form, name="save_form"),
    path('forms/<uuid:form_id>/publish/', views.publish_form, name='publish_form'),
    path('forms/<uuid:form_id>/access/', views.manage_access, name='manage_access'),
    path('f/<uuid:form_id>/', views.view_form, name='view_form'),
    path("settings/",views.settings_view,name='settings'),
    path('forms/<uuid:form_id>/responses/', views.view_responses, name='view_responses'),
    path('dashboard/', views.forms_list_view, name='forms_list'),
    path('forms/edit/<uuid:form_id>/', views.forms_view, name='edit_form'),
    path('f/<uuid:form_id>/submit/', views.submit_response, name='submit_response'),

    
  

    

    
]