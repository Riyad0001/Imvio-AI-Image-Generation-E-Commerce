from django.db import models


class NewsletterSubscription(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email


class FooterData(models.Model):
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    
    # Social Media Links
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    tiktok_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    
    # Copyright/Rights text
    all_rights_reserved = models.CharField(max_length=255, default="All Rights Reserved")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Footer Data"
        verbose_name_plural = "Footer Data"

    def __str__(self):
        return f"Footer Data - {self.contact_email}"


class Contact(models.Model):
    class Subject(models.TextChoices):
        GENERAL_INQUIRY = "general_inquiry", "General Inquiry"
        AI_GENERATION_QUESTION = "ai_generation_question", "AI Generation Question"
        PRINTING_DELIVERY = "printing_delivery", "Printing & Delivery"
        BILLING_CREDITS = "billing_credits", "Billing & Credits"
        TECHNICAL_ISSUE = "technical_issue", "Technical Issue"
        OTHERS = "others", "Others"

    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=32, choices=Subject.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} - {self.get_subject_display()}"

class GenExample(models.Model):
    prompt = models.TextField()
    image = models.ImageField(upload_to='gen_examples/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"GenExample - {self.prompt[:30]}..."