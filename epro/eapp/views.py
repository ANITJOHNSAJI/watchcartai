from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.conf import settings
import random
from datetime import datetime, timedelta
from .models import *
from django.urls import reverse
from django.contrib.auth.decorators import login_required
import razorpay
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pickle
import torch
from sentence_transformers import SentenceTransformer, util
# from read_content import *

# Initialize Sentence-BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

def getuser(request):
    return request.session.get('user') 

def types(request):
    type2 = []
    for i in Product.objects.all():
        if i.name and i.type not in type2:
            type2.append(i.type)
    return type2


# def process_reviews(reviews):
#     """Vectorize each review and return the average vector."""
#     if reviews:  # If there are reviews
#         review_list = reviews.split(',')  # Split reviews into individual comments
#         review_vectors = model.encode(review_list)  # Vectorize each review separately
#         review_vector = review_vectors.mean(axis=0)  # Calculate average of review vectors
#         return review_vector
#     else:
#         return None  

# def process_search(search):
#     if search:
#         search_list = search.split(',')
#         search_vectors = model.encode(search_list)
#         search_vector = search_vectors.mean(axis=0)
#         return search_vector
#     return None

# def combine_product_with_reviews(product_data):
#     combined_text = f"Product Name: {product_data['name']}, Rating: {product_data['rating']}, " \
#                     f"Type: {product_data['type']}, Description: {product_data['description']}"
#     return model.encode(combined_text)
# import pandas as pd
# # import pickle
# from sentence_transformers import SentenceTransformer

# # Initialize Sentence-BERT model
# model = SentenceTransformer('all-MiniLM-L6-v2')

# # Function to process and vectorize reviews for a course
# def process_reviews(reviews):
#     """Vectorize each review and return the average vector."""
#     if reviews:  # If there are reviews
#         review_list = reviews.split(',')  # Split reviews into individual comments
#         review_vectors = model.encode(review_list)  # Vectorize each review separately
#         review_vector = review_vectors.mean(axis=0)  # Calculate average of review vectors
#         return review_vector
#     else:
#         return None  # No reviews available
    

# def process_search(search):
#     if search:
#         search_list = search.split(',')
#         search_vectors = model.encode(search_list)
#         search_vector = search_vectors.mean(axis=0)
#         return search_vector

# # Function to combine product data and reviews to create a vector
# def combine_product_with_reviews(product_data):
#     """Combine product metadata and the review essence to generate a combined vector."""
#     combined_text = f"Product Name: {product_data['name']}, Rating: {product_data['rating']}, " \
#                     f"Type: {product_data['type']}, " \
#                     f"Description: {product_data['description']}"
    
#     product_vector = model.encode(combined_text)  # Vectorize the course metadata
#     review_vector = process_reviews(product_data['reviews'])  # Vectorize the reviews
    
#     if review_vector is not None:
#         combined_vector = product_vector + review_vector  # Combine the course vector and review vector
#     else:
#         combined_vector = product_vector  # If no reviews, just use the course data
#     print(combined_vector)
#     return combined_vector


# # Vectorize all courses with reviews
# def vectorize_product_with_reviews(df):
#     """Vectorize all product in the dataframe."""
#     product_vectors = []
#     for _, product in df.iterrows():
#         product_vector = combine_product_with_reviews(product)
#         product_vectors.append(product_vector)
#     return product_vectors

# def combine_user_with_search(user_data):
#     combined_text = f"user_id: {user_data['user_id']},  " \
#                     f"product: {user_data['product']}, " 
#     user_vector = model.encode(combined_text)
#     search_vector = process_search(user_data['search'])
#     if search_vector is not None:
#         combined_vector = user_vector + search_vector
#     else:
#         combined_vector = user_vector
#     return combined_vector
# def vectorize_user_with_search(df): 
#     user_vectors = []    
#     for _, user in df.iterrows():
#         user_vector = combine_user_with_search(user)
#         user_vectors.append(user_vector)
#     return user_vectors
# def vectorize_product_with_reviews(df):
#     return [combine_product_with_reviews(row) for _, row in df.iterrows()]





@login_required
def index(request):
    new_arrivals = Product.objects.all().order_by('-id')[:4]
    recommended_products = []

    if request.user.is_authenticated:
        try:
            user_obj = users.objects.get(name=request.user)
            view_history = ViewHistory.objects.filter(user=user_obj).select_related('product')
            viewed_product_ids = [vh.product.id for vh in view_history]
            
            product_df = get_product_data(products=Product.objects.exclude(id__in=viewed_product_ids)[:20])
            if product_df.empty:
                products = Product.objects.all()
                recommended_products = list(products[:4]) if products.count() <= 4 else sample(list(products), 4)
            else:
                user_df = get_user_data(request.user, user_obj, viewed_product_ids)
                user_vector = vectorize_user_with_search(user_df)[0]
                
                top_ids = recommend_products(user_vector, product_df)
                recommended_products = Product.objects.filter(id__in=top_ids)
                id_to_similarity = dict(zip(product_df['id'], product_df['similarity']))
                recommended_products = sorted(recommended_products, key=lambda x: id_to_similarity.get(x.id, 0), reverse=True)
        except users.DoesNotExist:
            products = Product.objects.all()
            recommended_products = list(products[:4]) if products.count() <= 4 else sample(list(products), 4)
    else:
        products = Product.objects.all()
        recommended_products = list(products[:4]) if products.count() <= 4 else sample(list(products), 4)
    
    return render(request, 'index.html', {
        'new_arrivals': new_arrivals,
        'recommended_products': recommended_products
    })
def product(request, id):
    product = get_object_or_404(Product, pk=id)
    cart_item_ids = []
    if request.user.is_authenticated:
        cart_item_ids = list(Cart.objects.filter(user=request.user).values_list('product_id', flat=True))
        # Log view history
        user_obj = users.objects.get(name=request.user)
        ViewHistory.objects.create(user=user_obj, product=product)
    return render(request, 'product.html', {
        'product': product,
        'cart_item_ids': cart_item_ids
    })

@login_required
def profile_view(request):
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by('-date_ordered')
    return render(request, 'profile.html', {
        'email': request.user.email,
        'addresses': addresses,
        'orders': orders
    })

@login_required
def add_address(request):
    if request.method == 'POST':
        name = request.POST.get('name', '')
        address = request.POST.get('address', '')
        phone = request.POST.get('phone', '')
        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not address:
            errors['address'] = 'Address is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'
        if not errors:
            Address.objects.create(
                user=request.user,
                name=name,
                address=address,
                phone=phone
            )
            messages.success(request, 'Address added successfully!')
            return redirect('profile')
        else:
            return render(request, 'address.html', {
                'errors': errors,
                'name': name,
                'address': address,
                'phone': phone,
                'action': 'Add'
            })
    return render(request, 'address.html', {'action': 'Add'})

@login_required
def edit_address(request, address_id):
    address_obj = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        name = request.POST.get('name', '')
        address = request.POST.get('address', '')
        phone = request.POST.get('phone', '')
        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not address:
            errors['address'] = 'Address is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'
        if not errors:
            address_obj.name = name
            address_obj.address = address
            address_obj.phone = phone
            address_obj.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('profile')
        else:
            return render(request, 'address.html', {
                'errors': errors,
                'name': name,
                'address': address,
                'phone': phone,
                'action': 'Edit'
            })
    return render(request, 'address.html', {
        'name': address_obj.name,
        'address': address_obj.address,
        'phone': address_obj.phone,
        'action': 'Edit'
    })

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully!')
        return redirect('profile')
    return render(request, 'confirm_delete.html', {'address': address})

@login_required
def edit_email(request):
    user = request.user
    if request.method == 'POST':
        email = request.POST.get('email', '')
        errors = {}
        if not email:
            errors['email'] = 'Email is required.'
        elif '@' not in email:
            errors['email'] = 'Please enter a valid email address.'
        if not errors:
            user.email = email
            user.save()
            messages.success(request, 'Email updated successfully!')
            return redirect('profile')
        else:
            return render(request, 'email.html', {
                'errors': errors,
                'email': email
            })
    return render(request, 'email.html', {
        'email': user.email
    })

@login_required
def edit_username(request):
    user = request.user
    if request.method == 'POST':
        username = request.POST.get('username', '')
        errors = {}
        if not username:
            errors['username'] = 'Username is required.'
        elif len(username) < 4:
            errors['username'] = 'Username should be at least 4 characters long.'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'This username is already taken.'
        if not errors:
            user.username = username
            user.save()
            messages.success(request, 'Username updated successfully!')
            return redirect('profile')
        else:
            return render(request, 'username.html', {
                'errors': errors,
                'username': username
            })
    return render(request, 'username.html', {
        'username': user.username
    })

def product_list(request):
    products = Product.objects.all()
    gender = request.GET.get('gender')
    if gender:
        products = products.filter(gender=gender)
    product_type = request.GET.get('display_type')
    if product_type:
        products = products.filter(type=product_type)
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(price__gte=min_price)
        except ValueError:
            pass
    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(price__lte=max_price)
        except ValueError:
            pass
    return render(request, 'allproduct.html', {'products': products})

def search_results(request):
    query = request.GET.get('q', '').strip()
    results = Product.objects.all()
    
    if query:
        if request.user.is_authenticated:
            user_obj, _ = users.objects.get_or_create(name=request.user)
            SearchHistory.objects.create(user=user_obj, query=query)
        
        # Search by name, type, or brand
        results = Product.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(type__icontains=query) |
            models.Q(brand__icontains=query)
        ).distinct()
        
        # Vector-based ranking
        product_df = get_product_data(products=Product.objects.all()[:50])
        if not product_df.empty:
            query_vector = model.encode(query).reshape(1, -1)
            
            if request.user.is_authenticated:
                user_df = get_user_data(request.user, user_obj)
                user_vector = vectorize_user_with_search(user_df)[0].reshape(1, -1)
                combined_vector = 0.7 * query_vector + 0.3 * user_vector
            else:
                combined_vector = query_vector
            
            top_ids = recommend_products(combined_vector, product_df, top_n=10)
            ranked_results = Product.objects.filter(id__in=top_ids)
            id_to_similarity = dict(zip(product_df['id'], product_df['similarity']))
            results = sorted(
                ranked_results,
                key=lambda x: id_to_similarity.get(x.id, 0),
                reverse=True
            ) if top_ids else results
        else:
            results = results[:10]  # Fallback to keyword search if no vectors
    
    # Pagination
    paginator = Paginator(results, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'search.html', {
        'page_obj': page_obj,
        'query': query,
        'types': Product.TYPE_CHOICES,
        'user': request.user
    })

def usersignup(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirmpassword = request.POST.get('confpassword')

        # Validation checks
        if not all([username, email, password, confirmpassword]):
            messages.error(request, 'All fields are required.')
        elif confirmpassword != password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
        else:
            try:
                # Create and save the Django User
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()

                # Create initial data for user vector
                user_datas = [{
                    "user_id": user.id,
                    "product": "new_user",  # Placeholder for viewed products
                    "search": "initial_signup"  # Placeholder for search history
                }]
                df = pd.DataFrame(user_datas)

                # Generate the vector
                user_vectors = vectorize_user_with_search(df)

                # Check if vectors were created
                if user_vectors and len(user_vectors) > 0:
                    # Create users model instance (use 'name' instead of 'user')
                    user_profile = users.objects.create(
                        name=user,  # Correct field name as per users model
                        vector_data=','.join(map(str, user_vectors[0]))  # Store as comma-separated string
                    )
                    user_profile.save()
                    print(f"Vector created and saved for user: {username}")
                else:
                    print(f"Failed to create vector for user: {username}")
                    # Create users instance without vector data
                    user_profile = users.objects.create(
                        name=user,
                        vector_data=None
                    )
                    user_profile.save()

                messages.success(request, "Account created successfully!")
                return redirect('userlogin')

            except Exception as e:
                print(f"Error during signup for {username}: {str(e)}")
                # Create users instance without vector data as fallback
                user_profile = users.objects.create(
                    name=user,
                    vector_data=None
                )
                user_profile.save()
                messages.success(request, "Account created, but personalization data could not be initialized.")
                return redirect('userlogin')

    return render(request, "register.html")

def userlogin(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('firstpage')
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
                return redirect('verifyotp')
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

def admin_bookings(request):
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        order.status = 'Confirmed'
        order.save()
        return redirect('admin_bookings')
    orders = Order.objects.all().order_by('-date_ordered')
    return render(request, 'admin_bookings.html', {'orders': orders})

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
            return redirect('edit_g', id=id)
        if type not in dict(Product.TYPE_CHOICES):
            messages.error(request, 'Invalid type choice.')
            return redirect('edit_g', id=id)
        product.name = name
        product.colour = colour
        product.price = price
        product.offerprice = offerprice
        product.description = description
        product.gender = gender
        product.type = type
        product.brand = brand
        product.quantity = quantity
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
        product.save()
        messages.success(request, "Product updated successfully!")
        return redirect('firstpage')
    return render(request, 'add.html', {
        'data1': product,
    })

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
        # Update product vector_data after creation
        review_texts = ''  # No reviews initially
        product_data = {
            'id': product.id,
            'name': product.name,
            'rating': product.rating,
            'type': product.type or '',
            'description': product.description,
            'reviews': review_texts
        }
        product_vector = combine_product_with_reviews(product_data)
        product.vector_data = ','.join(map(str, product_vector))
        product.save()
        messages.success(request, "Product added successfully!")
        return redirect('firstpage')
    return render(request, 'add.html')

@login_required(login_url='userlogin')
def add_to_cart(request, id):
    product = get_object_or_404(Product, id=id)
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product, defaults={'quantity': 1})
    if not created and cart_item.quantity < product.quantity:
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f"Quantity of {product.name} updated in your cart.")
    elif created:
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
def checkout_cart(request):
    cart_items = Cart.objects.filter(user=request.user)
    total_price = sum(item.get_total_price() for item in cart_items)
    default_address = Address.objects.filter(user=request.user, is_default=True).first()
    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'default_address': default_address
    })

@login_required(login_url='userlogin')
def checkout_single(request, id):
    product = get_object_or_404(Product, id=id)
    cart_items = [{
        'product': product,
        'quantity': 1,
        'get_total_price': lambda: product.offerprice
    }]
    total_price = product.offerprice
    default_address = Address.objects.filter(user=request.user, is_default=True).first()
    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'is_single': True,
        'product_id': product.id,
        'default_address': default_address
    })

@login_required(login_url='userlogin')
def process_checkout(request):
    if request.method == 'POST':
        address_choice = request.POST.get('address_choice')
        payment_method = request.POST.get('payment_method')
        is_single = request.POST.get('is_single') == 'True'
        product_id = request.POST.get('product_id')
        if address_choice == 'default':
            user_address = Address.objects.filter(user=request.user).first()
            if not user_address:
                messages.error(request, "No default address found.")
                return redirect('checkout_cart')
            shipping_address = user_address.address
            name = user_address.name
            phone = user_address.phone
        else:
            shipping_address = request.POST.get('address')
            name = request.POST.get('name')
            phone = request.POST.get('phone')
        if is_single and product_id:
            product = get_object_or_404(Product, id=product_id)
            total_price = product.offerprice
            order = Order.objects.create(
                user=request.user,
                name=name,
                phone=phone,
                shipping_address=shipping_address,
                payment_method=payment_method,
                total_price=total_price
            )
            OrderItem.objects.create(order=order, product=product, quantity=1)
        else:
            cart_items = Cart.objects.filter(user=request.user)
            total_price = sum(item.get_total_price() for item in cart_items)
            order = Order.objects.create(
                user=request.user,
                name=name,
                phone=phone,
                shipping_address=shipping_address,
                payment_method=payment_method,
                total_price=total_price
            )
            for item in cart_items:
                OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
            cart_items.delete()
        if payment_method == 'cod':
            order.is_paid = False
            order.save()
            return redirect('order_confirmation', order_id=order.id)
        else:
            return redirect('start_razorpay_payment', order_id=order.id)
    return redirect('cart_view')

@login_required(login_url='userlogin')
def start_razorpay_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if order.payment_method != 'online':
        messages.error(request, "Invalid payment method.")
        return redirect('cart_view')
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    amount = int(order.total_price * 100)  # Convert to paise
    data = {
        'amount': amount,
        'currency': 'INR',
        'receipt': f'order_{order.id}',
        'payment_capture': 1  # Auto capture
    }
    try:
        razorpay_order = client.order.create(data=data)
        order.razorpay_payment_id = razorpay_order['id']
        order.save()
        return render(request, 'payment.html', {
            'order': order,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': amount,
            'currency': 'INR',
            'name': order.name,
            'email': request.user.email,
            'contact': order.phone,
            'callback_url': request.build_absolute_uri(reverse('razorpay_callback')),
        })
    except Exception as e:
        messages.error(request, f"Error initiating payment: {str(e)}")
        return redirect('cart_view')

@csrf_exempt
def razorpay_callback(request):
    if request.method == 'POST':
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        payment_data = request.POST
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': payment_data.get('razorpay_order_id'),
                'razorpay_payment_id': payment_data.get('razorpay_payment_id'),
                'razorpay_signature': payment_data.get('razorpay_signature')
            })
            order = get_object_or_404(Order, razorpay_payment_id=payment_data.get('razorpay_order_id'))
            order.is_paid = True
            order.status = 'Confirmed'
            order.razorpay_payment_id = payment_data.get('razorpay_payment_id')
            order.save()
            messages.success(request, "Payment successful!")
            return redirect('order_confirmation', order_id=order.id)
        except Exception as e:
            messages.error(request, f"Payment verification failed: {str(e)}")
            return redirect('cart_view')
    return redirect('cart_view')

@login_required(login_url='userlogin')
def order_confirmation(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_confirmation.html', {'order': order})

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})

def first_page(request):
    products = Product.objects.all()
    return render(request, 'firstpage.html', {'products': products})