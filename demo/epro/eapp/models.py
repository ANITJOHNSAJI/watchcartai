from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator


class Product(models.Model):
    GENDER_CHOICES = [
        ('Female', 'Female'),
        ('Male', 'Male'),
        ('Unisex', 'Unisex'),
    ]
    
    TYPE_CHOICES = [
        ('Analogue', 'Analogue'),
        ('Digital', 'Digital'),
        ('Analogue/Digital', 'Analogue/Digital'),
    ]

    name = models.CharField(max_length=255)
    colour = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    offerprice = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, null=True, blank=True)
    brand = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    rating = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])
    vector_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.brand})"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')

    def __str__(self):
        return f"Image for {self.product.name}"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    vector_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.user.username


class SearchHistory(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    query = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.user.username}: {self.query}"


class ViewHistory(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.username} viewed {self.product.name}"


class Review(models.Model):
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    description = models.TextField()
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.user.username} for {self.product.name}"


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

    def get_total_price(self):
        return self.product.offerprice * self.quantity


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\+?1?\d{9,15}$', message="Phone number must be valid.")]
    )
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.address[:30]}"


class Order(models.Model):
    PAYMENT_METHODS = [
        ('online', 'Online Payment'),
        ('cod', 'Cash on Delivery'),
    ]

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    date_ordered = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username} on {self.date_ordered.strftime('%Y-%m-%d')}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"