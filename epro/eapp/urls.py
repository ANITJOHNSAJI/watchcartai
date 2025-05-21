from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings
from eapp import views

urlpatterns = [
    path('userlogin', views.userlogin,name='userlogin'),
    path('signup',views.usersignup,name='usersignup'),
    path('',views.index,name='index'),
    path('forgotpassword',views.getusername,name='forgotpassword'),
    path('verifyotp',views.verifyotp,name='verifyotp'),
    path('passwordreset',views.passwordreset,name='passwordreset'),
    path('logout/', views.logoutuser, name="logout"),
    path('adminbookings/', views.admin_bookings, name='admin_bookings'),   
    path('add/', views.add_product, name='add_product'),
    path('edit/<int:id>/', views.edit_g, name='edit_g'),
    path('delete/<int:id>/', views.delete_g, name='delete_g'),
    path('firstpage/', views.first_page, name='firstpage'),
    path('product/<int:id>/', views.product, name='product'),

    path('add_to_cart/<int:id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('increment_cart/<int:id>/', views.increment_cart, name='increment_cart'),
    path('decrement_cart/<int:id>/', views.decrement_cart, name='decrement_cart'),
    path('delete_cart_item/<int:id>/', views.delete_cart_item, name='delete_cart_item'),

    path('checkout/', views.checkout_cart, name='checkout'),  # full cart
    path('checkout/<int:id>/', views.checkout_single, name='checkout_single'),  # single product
    path('process_checkout/', views.process_checkout, name='process_checkout'),

    path('search/', views.search_results, name='search_results'),
    path('product_list/', views.product_list, name='product_list'), 
    path('profile/', views.profile_view, name='profile'),
    path('profile/add-address/', views.add_address, name='add_address'),
    path('profile/edit-address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('profile/delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('profile/edit-email/', views.edit_email, name='edit_email'),
    path('profile/edit-username/', views.edit_username, name='edit_username'),

    path('order_confirmation/<int:order_id>/',views.order_confirmation,name='order_confirmation'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),

    path('payment/<int:order_id>/', views.start_razorpay_payment, name='start_razorpay_payment'),
    path('payment/callback/', views.razorpay_callback, name='razorpay_callback'),

   
    
]

