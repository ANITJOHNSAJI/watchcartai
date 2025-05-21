from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


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
    price = models.DecimalField(max_digits=10, decimal_places=2)
    offerprice = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, null=True, blank=True)
    brand = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)
    image = models.ImageField(upload_to='products/')
    image1 = models.ImageField(upload_to='products/', blank=True, null=True)
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    image4 = models.ImageField(upload_to='products/', blank=True, null=True)
    image5 = models.ImageField(upload_to='products/', blank=True, null=True)
    rating = models.FloatField(default=0)
    vector_data = models.TextField(null=True, blank=True)  # Stores vector as comma-separated string

    def __str__(self):
        return self.name


class users(models.Model):
    name = models.ForeignKey(User, on_delete=models.CASCADE)
    vector_data = models.TextField(null=True, blank=True)  # Stores user vector data

    def __str__(self):
        return self.name.username


class SearchHistory(models.Model):
    query = models.CharField(max_length=255)
    user = models.ForeignKey(users, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.name.username}: {self.query}"


class ViewHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(users, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user.name.username} viewed {self.product.name}"


class reviews(models.Model):
    rating = models.IntegerField()
    description = models.TextField()
    uname = models.ForeignKey(users, on_delete=models.CASCADE)
    pname = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self):
        return f"Review by {self.uname.name.username} for {self.pname.name}"


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.quantity} of {self.product.name}'

    def get_total_price(self):
        return self.product.offerprice * self.quantity


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)  # Increased to 255 for consistency
    address = models.TextField()
    phone = models.CharField(max_length=12)
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
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    shipping_address = models.TextField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    date_ordered = models.DateTimeField(auto_now_add=True)
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"