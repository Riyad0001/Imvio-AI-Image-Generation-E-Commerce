from django_ckeditor_5.fields import CKEditor5Field
from django.db import models
from apps.sub.models import ProductSize
class ProductType(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to="types/")
    
    def __str__(self):
        return self.name


class ProductVariant(models.Model):
    product_type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    size = models.ForeignKey(ProductSize, on_delete=models.CASCADE)
    gelato_product_uid = models.CharField(max_length=200, blank=True, default="", help_text="Gelato product UID for this specific type and size combination")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)


    def __str__(self):
        return f"{self.product_type} - {self.size}"


class Other_pages(models.Model):
    name = models.CharField(max_length=100)
    content = CKEditor5Field("Content", config_name="extends")
    types=models.CharField(max_length=50,choices=[('terms','Terms'),('privacy','Privacy'),('refund','Refund'),('shipping','Shipping')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name