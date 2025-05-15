from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

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
    vector_data = models.TextField(null=True, blank=True)  # Store product vector

    def __str__(self):
        return self.name

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    vector_data = models.TextField(null=True, blank=True)  # Store user vector

    def __str__(self):
        return self.user.username

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.quantity} of {self.product.name}'

    def get_total_price(self):
        return self.product.offerprice * self.quantity

class Review(models.Model):
    rating = models.IntegerField()  # 1-5
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review for {self.product.name} by {self.user.username}'

class ViewHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']

class SearchHistory(models.Model):
    query = models.CharField(max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    searched_at = models.DateTimeField(auto_now_add=True)