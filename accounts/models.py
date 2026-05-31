from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('role', CustomUser.SUPER_ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)


class Company(models.Model):
    ERP_TYPES = [('odoo', 'Odoo')]
    INDUSTRIES = [
        ('manufacturing', 'Manufacturing'),
        ('retail', 'Retail'),
        ('logistics', 'Logistics'),
        ('healthcare', 'Healthcare'),
        ('finance', 'Finance'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=255)
    erp_type = models.CharField(max_length=50, choices=ERP_TYPES, default='odoo')
    industry = models.CharField(max_length=100, choices=INDUSTRIES)
    company_code = models.CharField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.company_code:
            # Auto-generate: ERP-OD-XXXX
            last = Company.objects.order_by('id').last()
            next_id = (last.id + 1) if last else 1
            self.company_code = f"ERP-OD-{1000 + next_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.company_code})"

    class Meta:
        verbose_name_plural = "Companies"


class CustomUser(AbstractBaseUser, PermissionsMixin):
    SUPER_ADMIN = 'super_admin'
    ADMIN = 'admin'
    EMPLOYEE = 'employee'

    ROLE_CHOICES = [
        (SUPER_ADMIN, 'Super Admin'),
        (ADMIN, 'Admin'),
        (EMPLOYEE, 'Employee'),
    ]

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=EMPLOYEE)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.username} ({self.role})"

    def is_super_admin(self):
        return self.role == self.SUPER_ADMIN

    def is_admin(self):
        return self.role == self.ADMIN

    def is_employee(self):
        return self.role == self.EMPLOYEE


class RegisteredEmployee(models.Model):
    """Emails pre-registered by Admin before employee can sign up."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    email = models.EmailField()
    business_process = models.CharField(max_length=255)
    is_registered = models.BooleanField(default=False)  # True once they sign up

    class Meta:
        unique_together = ('company', 'email')

    def __str__(self):
        return f"{self.email} → {self.business_process}"

class BusinessProcess(models.Model):
    PREDEFINED_PROCESSES = [
        ('procure_to_pay', 'Procure-to-Pay'),
        ('order_to_cash', 'Order-to-Cash'),
        ('inventory_fulfillment', 'Inventory Fulfillment'),
        ('employee_management', 'Employee Management'),
        ('custom', 'Custom'),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    process_type = models.CharField(max_length=50, choices=PREDEFINED_PROCESSES, default='custom')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.company.name}"

    class Meta:
        unique_together = ('company', 'name')



# ↓ invitation link for employee ↓

class EmployeeInvitation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    email = models.EmailField()
    business_process = models.CharField(max_length=255)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} — {self.company.name}"
    
# survey questions

class EvaluationQuestion(models.Model):
    CATEGORIES = [
        ('system_quality', 'System Quality'),
        ('information_quality', 'Information Quality'),
        ('process_efficiency', 'Process Efficiency'),
        ('user_satisfaction', 'User Satisfaction'),
        ('perceived_roi', 'Perceived ROI'),
    ]

    QUESTION_TYPES = [
        ('predefined', 'Predefined'),
        ('custom', 'Custom'),
    ]

    # Null company = global predefined question template
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    business_process = models.ForeignKey(BusinessProcess, on_delete=models.CASCADE, null=True, blank=True)
    process_type = models.CharField(max_length=50, blank=True)  # links to predefined process type
    category = models.CharField(max_length=50, choices=CATEGORIES)
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='predefined')
    diagnosis_tag = models.CharField(max_length=100, blank=True)
    diagnosis_message = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_category_display()}] {self.question_text[:60]}"

    class Meta:
        ordering = ['category', 'id']

#eveluation responses

class EvaluationResponse(models.Model):
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    business_process = models.ForeignKey(BusinessProcess, on_delete=models.CASCADE)
    question = models.ForeignKey(EvaluationQuestion, on_delete=models.CASCADE)
    rating = models.IntegerField()  # 1-5 Likert scale
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'question')

    def __str__(self):
        return f"{self.employee.username} — {self.question.diagnosis_tag} — {self.rating}"

#getting category feedback
class CategoryFeedback(models.Model):
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    business_process = models.ForeignKey(BusinessProcess, on_delete=models.CASCADE)
    category = models.CharField(max_length=50)
    feedback_text = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('employee', 'business_process', 'category')

    def __str__(self):
        return f"{self.employee.username} — {self.category}"