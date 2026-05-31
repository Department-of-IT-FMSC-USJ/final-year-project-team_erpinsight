from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Company, RegisteredEmployee
from .models import BusinessProcess



@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'username', 'role', 'company', 'is_active')
    list_filter = ('role', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Role & Company', {'fields': ('role', 'company')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'username', 'password1', 'password2', 'role', 'company')}),
    )
    search_fields = ('email', 'username')
    ordering = ('email',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'company_code', 'erp_type', 'industry', 'is_active', 'created_at')
    search_fields = ('name', 'company_code')
    readonly_fields = ('company_code',)


@admin.register(RegisteredEmployee)
class RegisteredEmployeeAdmin(admin.ModelAdmin):
    list_display = ('email', 'company', 'business_process', 'is_registered')
    list_filter = ('company', 'is_registered')
    search_fields = ('email',)

@admin.register(BusinessProcess)
class BusinessProcessAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'process_type', 'is_active', 'created_at')
    list_filter = ('company', 'is_active')


