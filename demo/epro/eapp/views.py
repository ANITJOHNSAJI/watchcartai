from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.conf import settings
import random
from datetime import datetime, timedelta
from .models import Product, ProductImage, UserProfile, SearchHistory, ViewHistory, Review, Cart, Address, Order, OrderItem
from django.urls import reverse
from django.contrib.auth.decorators import login_required
import razorpay
from django.views.decorators.csrf import csrf_exempt
from .read_content import recommend_product
from .vectorize import vectorize_product_with_reviews, vectorize_user_with_search

def index(request):
    # Display the latest 4 products and personalized recommendations if user is authenticated
    products = Product.objects.all().order_by('-id')[:4]
    recommended_products = []
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            recommended_products = recommend_product("", user=request.user, top_n=4)
            recommended_products = [
                get_object_or_404(Product, id=prod_id) for prod_id, _, _ in recommended_products
            ]
        except UserProfile.DoesNotExist:
            pass
    return render(request, "index.html", {
        "products": products,
        "recommended_products": recommended_products
    })

def product(request, id):
    # Display product details and add to view history if authenticated
    product = get_object_or_404(Product, pk=id)
    cart_item_ids = []
    if request.user.is_authenticated:
        cart_item_ids = list(Cart.objects.filter(user=request.user).values_list('product_id', flat=True))
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            ViewHistory.objects.create(user=user_profile, product=product)
        except UserProfile.DoesNotExist:
            pass
    return render(request, 'product.html', {
        'product': product,
        'cart_item_ids': cart_item_ids,
        'images': product.images.all()  # Fetch related images
    })

@login_required
def profile_view(request):
    # Display user profile with addresses and orders
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
        is_default = request.POST.get('is_default', False) == 'on'
        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not address:
            errors['address'] = 'Address is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'
        try:
            from django.core.validators import RegexValidator
            phone_validator = RegexValidator(r'^\+?1?\d{9,15}$', message="Phone number must be valid.")
            phone_validator(phone)
        except:
            errors['phone'] = 'Phone number must be valid.'
        if not errors:
            # If setting as default, unset other default addresses
            if is_default:
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            Address.objects.create(
                user=request.user,
                name=name,
                address=address,
                phone=phone,
                is_default=is_default
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
        is_default = request.POST.get('is_default', False) == 'on'
        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not address:
            errors['address'] = 'Address is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'
        try:
            from django.core.validators import RegexValidator
            phone_validator = RegexValidator(r'^\+?1?\d{9,15}$', message="Phone number must be valid.")
            phone_validator(phone)
        except:
            errors['phone'] = 'Phone number must be valid.'
        if not errors:
            if is_default:
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
            address_obj.name = name
            address_obj.address = address
            address_obj.phone = phone
            address_obj.is_default = is_default
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
        'is_default': address_obj.is_default,
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
        elif User.objects.filter(email=email).exclude(id=user.id).exists():
            errors['email'] = 'This email is already in use.'
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
        elif User.objects.filter(username=username).exclude(id=user.id).exists():
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
    if gender and gender in dict(Product.GENDER_CHOICES):
        products = products.filter(gender=gender)
    product_type = request.GET.get('display_type')
    if product_type and product_type in dict(Product.TYPE_CHOICES):
        products = products.filter(type=product_type)
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        try:
            min_price = float(min_price)
            products = products.filter(offerprice__gte=min_price)
        except ValueError:
            pass
    if max_price:
        try:
            max_price = float(max_price)
            products = products.filter(offerprice__lte=max_price)
        except ValueError:
            pass
    return render(request, 'allproduct.html', {'products': products})

def search_results(request):
    query = request.GET.get('q', '').strip()
    results = []
    recommended_products = []
    if query:
        # Save search query to history if user is authenticated
        if request.user.is_authenticated:
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                SearchHistory.objects.create(user=user_profile, query=query)
                # Update user vector
                vectorize_user_with_search()
            except UserProfile.DoesNotExist:
                pass
        # Basic search
        results = Product.objects.filter(name__icontains=query) | \
                  Product.objects.filter(description__icontains=query) | \
                  Product.objects.filter(brand__icontains=query)
        # Personalized recommendations
        recommended_products = recommend_product(query, user=request.user if request.user.is_authenticated else None, top_n=5)
        recommended_products = [
            get_object_or_404(Product, id=prod_id) for prod_id, _, _ in recommended_products
        ]
    else:
        results = Product.objects.all()
    return render(request, 'search.html', {
        'results': results,
        'query': query,
        'recommended_products': recommended_products
    })

def usersignup(request):
    if request.method == "POST":
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirmpassword = request.POST.get('confpassword')
        errors = {}
        if not username or not email or not password or not confirmpassword:
            errors['general'] = 'All fields are required.'
        elif confirmpassword != password:
            errors['password'] = "Passwords do not match."
        elif User.objects.filter(email=email).exists():
            errors['email'] = "Email already exists."
        elif User.objects.filter(username=username).exists():
            errors['username'] = "Username already exists."
        if not errors:
            user = User.objects.create_user(username=username, email=email, password=password)
            UserProfile.objects.create(user=user)  # Create UserProfile
            messages.success(request, "Account created successfully!")
            return redirect('userlogin')
        else:
            return render(request, "register.html", {'errors': errors})
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
                return redirect('getusername')
        if otp == otp1:
            del request.session['otp']
            del request.session['otp_time']
            return redirect('passwordreset')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    else:
        # Generate OTP only if none exists
        if not request.session.get('otp'):
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
    return render(request, 'getusername.html')

def passwordreset(request):
    if request.method == 'POST':
        password = request.POST.get('password')
        confirmpassword = request.POST.get('confpassword')
        errors = {}
        if not password or not confirmpassword:
            errors['password'] = "Both password fields are required."
        elif confirmpassword != password:
            errors['password'] = "Passwords do not match."
        if not errors:
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
        else:
            return render(request, "passwordreset.html", {'errors': errors})
    return render(request, "passwordreset.html")

@login_required
def admin_bookings(request):
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Order, id=order_id)
        order.status = 'Confirmed'
        order.save()
        messages.success(request, "Order confirmed successfully.")
        return redirect('admin_bookings')
    orders = Order.objects.all().order_by('-date_ordered')
    return render(request, 'admin_bookings.html', {'orders': orders})

@login_required
def delete_g(request, id):
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('index')
    product = get_object_or_404(Product, pk=id)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect('firstpage')

@login_required
def edit_g(request, id):
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('index')
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
        images = request.FILES.getlist('images')  # Handle multiple images
        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not colour:
            errors['colour'] = 'Colour is required.'
        if not price or not offerprice:
            errors['price'] = 'Price and offer price are required.'
        if not description:
            errors['description'] = 'Description is required.'
        if not brand:
            errors['brand'] = 'Brand is required.'
        if not quantity:
            errors['quantity'] = 'Quantity is required.'
        if gender and gender not in dict(Product.GENDER_CHOICES):
            errors['gender'] = 'Invalid gender choice.'
        if type and type not in dict(Product.TYPE_CHOICES):
            errors['type'] = 'Invalid type choice.'
        try:
            price = float(price)
            offerprice = float(offerprice)
            quantity = int(quantity)
            if price < 0 or offerprice < 0 or quantity < 0:
                errors['general'] = 'Price, offer price, and quantity must be non-negative.'
        except ValueError:
            errors['general'] = 'Invalid number format for price, offer price, or quantity.'
        if not errors:
            product.name = name
            product.colour = colour
            product.price = price
            product.offerprice = offerprice
            product.description = description
            product.gender = gender if gender else None
            product.type = type if type else None
            product.brand = brand
            product.quantity = quantity
            product.save()
            # Handle image uploads
            if images:
                product.images.all().delete()  # Remove existing images
                for image in images:
                    ProductImage.objects.create(product=product, image=image)
            # Update product vector
            vectorize_product_with_reviews()
            messages.success(request, "Product updated successfully!")
            return redirect('firstpage')
        else:
            return render(request, 'add.html', {
                'data1': product,
                'errors': errors,
                'images': product.images.all()
            })
    return render(request, 'add.html', {
        'data1': product,
        'images': product.images.all()
    })

@login_required
def add_product(request):
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to perform this action.")
        return redirect('index')
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
        images = request.FILES.getlist('images')  # Handle multiple images
        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not colour:
            errors['colour'] = 'Colour is required.'
        if not price or not offerprice:
            errors['price'] = 'Price and offer price are required.'
        if not description:
            errors['description'] = 'Description is required.'
        if not brand:
            errors['brand'] = 'Brand is required.'
        if not quantity:
            errors['quantity'] = 'Quantity is required.'
        if gender and gender not in dict(Product.GENDER_CHOICES):
            errors['gender'] = 'Invalid gender choice.'
        if type and type not in dict(Product.TYPE_CHOICES):
            errors['type'] = 'Invalid type choice.'
        try:
            price = float(price)
            offerprice = float(offerprice)
            quantity = int(quantity)
            if price < 0 or offerprice < 0 or quantity < 0:
                errors['general'] = 'Price, offer price, and quantity must be non-negative.'
        except ValueError:
            errors['general'] = 'Invalid number format for price, offer price, or quantity.'
        if not errors:
            product = Product.objects.create(
                name=name,
                colour=colour,
                price=price,
                offerprice=offerprice,
                description=description,
                gender=gender if gender else None,
                type=type if type else None,
                brand=brand,
                quantity=quantity
            )
            # Handle image uploads
            for image in images:
                ProductImage.objects.create(product=product, image=image)
            # Update product vector
            vectorize_product_with_reviews()
            messages.success(request, "Product added successfully!")
            return redirect('firstpage')
        else:
            return render(request, 'add.html', {'errors': errors})
    return render(request, 'add.html')

@login_required(login_url='userlogin')
def add_to_cart(request, id):
    product = get_object_or_404(Product, id=id)
    if product.quantity <= 0:
        messages.error(request, "Sorry, this product is out of stock.")
        return redirect('product', id=id)
    cart_item, created = Cart.objects.get_or_create(user=request.user, product=product, defaults={'quantity': 1})
    if not created and cart_item.quantity < product.quantity:
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f"Quantity of {product.name} updated in your cart.")
    elif created:
        messages.success(request, f"{product.name} has been added to your cart.")
    else:
        messages.error(request, "Sorry, no more stock available.")
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
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    total_price = sum(item.get_total_price() for item in cart_items)
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total_price': total_price,
    })

@login_required(login_url='userlogin')
def checkout_cart(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    if not cart_items:
        messages.error(request, "Your cart is empty.")
        return redirect('cart_view')
    total_price = sum(item.get_total_price() for item in cart_items)
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()
    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'addresses': addresses,
        'default_address': default_address,
        'is_single': False
    })

@login_required(login_url='userlogin')
def checkout_single(request, id):
    product = get_object_or_404(Product, id=id)
    if product.quantity <= 0:
        messages.error(request, "Sorry, this product is out of stock.")
        return redirect('product', id=id)
    cart_items = [Cart(user=request.user, product=product, quantity=1)]  # Create a temporary Cart object
    total_price = product.offerprice
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()
    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'total_price': total_price,
        'addresses': addresses,
        'default_address': default_address,
        'is_single': True,
        'product_id': product.id
    })

@login_required(login_url='userlogin')
def process_checkout(request):
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        payment_method = request.POST.get('payment_method')
        is_single = request.POST.get('is_single') == 'True'
        product_id = request.POST.get('product_id')
        if not address_id:
            messages.error(request, "Please select an address.")
            return redirect('checkout_cart' if not is_single else 'checkout_single', id=product_id if is_single else None)
        address = get_object_or_404(Address, id=address_id, user=request.user)
        if payment_method not in dict(Order.PAYMENT_METHODS):
            messages.error(request, "Invalid payment method.")
            return redirect('checkout_cart' if not is_single else 'checkout_single', id=product_id if is_single else None)
        try:
            if is_single and product_id:
                product = get_object_or_404(Product, id=product_id)
                if product.quantity < 1:
                    messages.error(request, "Product is out of stock.")
                    return redirect('checkout_single', id=product_id)
                total_price = product.offerprice
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    payment_method=payment_method,
                    total_price=total_price,
                    is_paid=False
                )
                OrderItem.objects.create(order=order, product=product, quantity=1)
                product.quantity -= 1
                product.save()
            else:
                cart_items = Cart.objects.filter(user=request.user).select_related('product')
                if not cart_items:
                    messages.error(request, "Your cart is empty.")
                    return redirect('cart_view')
                total_price = sum(item.get_total_price() for item in cart_items)
                order = Order.objects.create(
                    user=request.user,
                    address=address,
                    payment_method=payment_method,
                    total_price=total_price,
                    is_paid=False
                )
                for item in cart_items:
                    if item.product.quantity < item.quantity:
                        order.delete()
                        messages.error(request, f"Not enough stock for {item.product.name}.")
                        return redirect('cart_view')
                    OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
                    item.product.quantity -= item.quantity
                    item.product.save()
                cart_items.delete()
            if payment_method == 'cod':
                order.is_paid = False
                order.status = 'Pending'
                order.save()
                return redirect('order_confirmation', order_id=order.id)
            else:
                return redirect('start_razorpay_payment', order_id=order.id)
        except Exception as e:
            messages.error(request, f"Error processing order: {str(e)}")
            return redirect('cart_view')
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
            'name': order.address.name,
            'email': request.user.email,
            'contact': order.address.phone,
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

@login_required(login_url='userlogin')
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_detail.html', {'order': order})

@login_required
def first_page(request):
    if not request.user.is_superuser:
        messages.error(request, "You are not authorized to access this page.")
        return redirect('index')
    products = Product.objects.all()
    return render(request, 'firstpage.html', {'products': products})