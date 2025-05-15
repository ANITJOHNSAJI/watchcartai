from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.conf import settings
import random
from datetime import datetime, timedelta
from .models import Product, Cart, Profile, Review, ViewHistory, SearchHistory
from django.urls import reverse
from django.contrib.auth.decorators import login_required
import pandas as pd
import json
import torch
import numpy as np
from .vectorize import vectorize_product_with_reviews, vectorize_user_with_search, recommend_product



def index(request):
    products = Product.objects.all()[:8]  # Changed from all_products
    product_ids = [p.id for p in Product.objects.all()]
    product_vectors = [json.loads(p.vector_data) for p in Product.objects.all() if p.vector_data]
    product_vectors = torch.tensor(np.array(product_vectors)) if product_vectors else torch.tensor([])

    recommended = Product.objects.order_by('-id')[:4]
    if request.user.is_authenticated and product_vectors.shape[0] > 0:
        try:
            profile = Profile.objects.get(user=request.user)
            user_vector = json.loads(profile.vector_data) if profile.vector_data else None
            if user_vector:
                recommended_ids = recommend_product(user_vector, product_vectors, product_ids, top_n=4)
                recommended = Product.objects.filter(id__in=[i[0] for i in recommended_ids]).order_by('-id')
        except Profile.DoesNotExist:
            pass

    return render(request, 'index.html', {
        'products': products,
        'recommended': recommended,
        'user': request.user,
    })
def product(request, id):
    product = get_object_or_404(Product, pk=id)
    cart_item_ids = []
    if request.user.is_authenticated:
        cart_item_ids = list(Cart.objects.filter(user=request.user).values_list('product_id', flat=True))
        # Log view history
        ViewHistory.objects.get_or_create(user=request.user, product=product)
        # Update user vector
        update_user_vector(request.user)

    return render(request, 'product.html', {
        'product': product,
        'cart_item_ids': cart_item_ids
    })



def product_list(request):
    products = Product.objects.all()
    
    # Get filter parameters from request
    gender = request.GET.get('gender')
    if gender:
        products = products.filter(gender=gender)

    # Fix: Use 'type' instead of 'display_type'
    product_type = request.GET.get('display_type')  
    if product_type:
        products = products.filter(type=product_type)  # Change 'display_type' to 'type'

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
        except ValueError:
            pass  # Ignore invalid price input

    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
        except ValueError:
            pass  # Ignore invalid price input

    # Render template with filtered products
    return render(request, 'allproduct.html', {'products': products})


def search_results(request):
    query = request.GET.get('q')
    results = Product.objects.all()
    
    if query:
        results = Product.objects.filter(name__icontains=query)
        if request.user.is_authenticated:
            SearchHistory.objects.create(user=request.user, query=query)
            update_user_vector(request.user)

    return render(request, 'search.html', {'results': results, 'query': query})

def usersignup(request):
    if request.method == "POST":
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirmpassword = request.POST.get('confpassword')
        
        if not username or not email or not password or not confirmpassword:
            messages.error(request, 'All fields are required.')
        elif confirmpassword != password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            # Create profile and initial vector
            Profile.objects.create(user=user)
            update_user_vector(user)
            messages.success(request, "Account created successfully!")
            return redirect('userlogin')

    return render(request, "register.html")

@login_required(login_url='userlogin')
def add_review(request, id):
    product = get_object_or_404(Product, id=id)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        description = request.POST.get('description')
        try:
            rating = int(rating)
            if 1 <= rating <= 5:
                Review.objects.create(
                    user=request.user,
                    product=product,
                    rating=rating,
                    description=description
                )
                # Update product rating
                reviews = Review.objects.filter(product=product)
                product.rating = sum(r.rating for r in reviews) / reviews.count() if reviews else 0
                product.save()
                # Update product vector
                update_product_vector(product)
                messages.success(request, "Review added successfully!")
            else:
                messages.error(request, "Rating must be between 1 and 5.")
        except ValueError:
            messages.error(request, "Invalid rating.")
        return redirect('product', id=id)
    return render(request, 'add_review.html')

def update_product_vector(product):
    """Update the vector_data for a product."""
    reviews = ','.join(r.description for r in Review.objects.filter(product=product))
    df = pd.DataFrame([{
        'pro_id': product.id,
        'name': product.name,
        'rating': getattr(product, 'rating', 0),
        'type': product.type or '',
        'gender': product.gender or '',
        'brand': product.brand,
        'description': product.description,
        'reviews': reviews
    }])
    product_vector = vectorize_product_with_reviews(df)[0]
    product.vector_data = json.dumps(product_vector.tolist())
    product.save()

def update_user_vector(user):
    """Update the vector_data for a user."""
    viewed_products = ','.join(p.name for p in Product.objects.filter(viewhistory__user=user))
    searches = ','.join(s.query for s in SearchHistory.objects.filter(user=user))
    df = pd.DataFrame([{
        'user_id': user.id,
        'product': viewed_products,
        'search': searches
    }])
    user_vector = vectorize_user_with_search(df)[0]
    profile, created = Profile.objects.get_or_create(user=user)
    profile.vector_data = json.dumps(user_vector.tolist())
    profile.save()

def userlogin(request):
    if request.user.is_authenticated:  # Instead of checking session directly
        return redirect('index')  

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('firstpage')  # Check that the 'firstpage' URL exists
            return redirect('index')
        else:
            messages.error(request, "Invalid credentials.")

    return render(request, 'userlogin.html')


def logoutuser(request):
    logout(request)
    request.session.flush()
    return redirect('userlogin')


def verifyotp(request):
    if request.method == "POST":
        otp = request.POST.get('otp')
        otp1 = request.session.get('otp')
        otp_time_str = request.session.get('otp_time')

        if otp_time_str:
            otp_time = datetime.fromisoformat(otp_time_str)
            otp_expiry_time = otp_time + timedelta(minutes=5)
            if datetime.now() > otp_expiry_time:
                messages.error(request, 'OTP has expired. Please request a new one.')
                del request.session['otp']
                del request.session['otp_time']
                return redirect('verifyotp')  # Allow user to request a new OTP

        if otp == otp1:
            del request.session['otp']
            del request.session['otp_time']
            return redirect('passwordreset')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    otp = ''.join(random.choices('123456789', k=6))
    request.session['otp'] = otp
    request.session['otp_time'] = datetime.now().isoformat()

    message = f'Your email verification code is: {otp}'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [request.session.get('email')]
    send_mail('Email Verification', message, email_from, recipient_list)

    return render(request, "otp.html")



def getusername(request):
    if request.method == "POST":
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            request.session['email'] = user.email
            return redirect('verifyotp')
        except User.DoesNotExist:
            messages.error(request, "Username does not exist.")
            return redirect('getusername')

    return render(request, 'getusername.html')


def passwordreset(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        confirmpassword = request.POST.get('confpassword')

        if confirmpassword != password:
            messages.error(request, "Passwords do not match.")
        else:
            email = request.session.get('email')
            try:
                user = User.objects.get(email=email)
                user.set_password(password)
                user.save()
                del request.session['email']
                messages.success(request, "Your password has been reset successfully.")

                user = authenticate(username=user.username, password=password)
                if user is not None:
                    login(request, user)

                return redirect('userlogin') 
            except User.DoesNotExist:
                messages.error(request, "No user found with that email address.")
                return redirect('getusername') 

    return render(request, "passwordreset.html")





def category(request):
    return render(request, 'category.html')


def bookings(request):
    return render(request, 'bookings.html')


def delete_g(request, id):
    product = get_object_or_404(Product, pk=id)
    product.delete()
    return redirect('firstpage')


def edit_g(request, id):
    product = get_object_or_404(Product, pk=id)

    if request.method == 'POST':
        name = request.POST.get('name')
        colour = request.POST.get('colour')
        price = request.POST.get('price')
        offerprice = request.POST.get('offerprice')
        description = request.POST.get('description')
        gender = request.POST.get('gender')  # 'Female', 'Male', or 'Unisex'
        type = request.POST.get('type')  # 'Digital', 'Analogue', or 'Analogue/Digital'
        brand = request.POST.get('brand')
        quantity = request.POST.get('quantity')
        image = request.FILES.get('image')
        image1 = request.FILES.get('image1')
        image2 = request.FILES.get('image2')
        image3 = request.FILES.get('image3')
        image4 = request.FILES.get('image4')
        image5 = request.FILES.get('image5')

        # Ensure gender and type are from the predefined choices
        if gender not in dict(Product.GENDER_CHOICES):
            messages.error(request, 'Invalid gender choice.')
            return redirect('edit_g', id=id)
        if type not in dict(Product.TYPE_CHOICES):
            messages.error(request, 'Invalid type choice.')
            return redirect('edit_g', id=id)

        # Update the product fields
        product.name = name
        product.colour = colour
        product.price = price
        product.offerprice = offerprice
        product.description = description
        product.gender = gender
        product.type = type
        product.brand = brand
        product.quantity = quantity

        # If images are uploaded, update them
        if image:
            product.image = image
        if image1:
            product.image1 = image1
        if image2:
            product.image2 = image2
        if image3:
            product.image3 = image3
        if image4:
            product.image4 = image4
        if image5:
            product.image5 = image5

        product.save()  # Save the updated product
        messages.success(request, "Product updated successfully!")
        return redirect('firstpage')

    return render(request, 'add.html', {
        'data1': product,
    })

# Add a New Product
# Existing views (add_product, edit_g, etc.) remain mostly unchanged
# Update add_product to compute vector
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        colour = request.POST.get('colour')
        price = request.POST.get('price')
        offerprice = request.POST.get('offerprice')
        description = request.POST.get('description')
        gender = request.POST.get('gender')
        type = request.POST.get('type')
        brand = request.POST.get('brand')
        quantity = request.POST.get('quantity')
        image = request.FILES.get('image')
        image1 = request.FILES.get('image1')
        image2 = request.FILES.get('image2')
        image3 = request.FILES.get('image3')
        image4 = request.FILES.get('image4')
        image5 = request.FILES.get('image5')

        if gender not in dict(Product.GENDER_CHOICES):
            messages.error(request, 'Invalid gender choice.')
            return redirect('add_product')
        if type not in dict(Product.TYPE_CHOICES):
            messages.error(request, 'Invalid type choice.')
            return redirect('add_product')

        product = Product.objects.create(
            name=name, colour=colour, price=price, offerprice=offerprice,
            description=description, gender=gender, type=type, brand=brand, quantity=quantity,
            image=image, image1=image1, image2=image2, image3=image3, image4=image4, image5=image5
        )
        update_product_vector(product)
        messages.success(request, "Product added successfully!")
        return redirect('firstpage')

    return render(request, 'add.html')

@login_required(login_url='userlogin')
def add_to_cart(request, id):
    product = get_object_or_404(Product, id=id)

    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product)

    if cart_item.quantity < product.quantity:
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f"{product.name} has been added to your cart.")
    else:
        messages.error(request, "Sorry, this product is out of stock.")

    return redirect('cart_view')

@login_required(login_url='userlogin')
def increment_cart(request, id):
    cart_item = get_object_or_404(Cart, id=id, user=request.user)

    if cart_item.quantity < cart_item.product.quantity:
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, "Quantity updated.")
    else:
        messages.error(request, "No more stock available.")

    return redirect('cart_view')

@login_required(login_url='userlogin')
def decrement_cart(request, id):
    cart_item = get_object_or_404(Cart, id=id, user=request.user)

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        cart_item.save()
        messages.success(request, "Quantity updated.")
    else:
        cart_item.delete()
        messages.success(request, "Item removed from cart.")

    return redirect('cart_view')

@login_required(login_url='userlogin')
def delete_cart_item(request, id):
    cart_item = get_object_or_404(Cart, id=id, user=request.user)
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart_view')

@login_required(login_url='userlogin')
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user)
    total_price = sum(item.get_total_price() for item in cart_items)

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
    })

@login_required(login_url='userlogin')
def checkout(request):
    # Get the cart items for the logged-in user
    cart_items = Cart.objects.filter(user=request.user)
    
    # Calculate the total price by summing up the prices of the cart items
    total_price = sum(item.get_total_price() for item in cart_items)
    
    # Render the checkout page with the cart items and total price
    return render(request, 'checkout.html', {'cart_items': cart_items, 'total_price': total_price})


def process_checkout(request):
    if request.method == 'POST':
        # Handle checkout logic: Save the order, process payment, etc.
        address = request.POST.get('address')
        payment_method = request.POST.get('payment_method')
        
        # Example order creation (you would need to implement actual order processing)
        order = Order.objects.create(
            user=request.user,
            shipping_address=address,
            payment_method=payment_method,
            total_price=total_price  # You'd calculate this beforehand
        )
        
        # Redirect to an order confirmation page or summary page
        return redirect('order_confirmation', order_id=order.id)

    return redirect('cart_view')

# First Page (Product Listing)
def first_page(request):
    products = Product.objects.all()
    return render(request, 'firstpage.html', {'products': products})

