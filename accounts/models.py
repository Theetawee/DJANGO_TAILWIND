import os

from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models


class AccountManager(BaseUserManager):
    def create_user(self, email, username, name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        if not username:
            raise ValueError("The Username field must be set")
        if not name:
            raise ValueError("The Name field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, username=username, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, name, password, **extra_fields)


class Account(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=10, unique=True)
    email = models.EmailField(max_length=255, unique=True, verbose_name="Email")
    phone = models.CharField(null=True, blank=True, max_length=12)
    profile_image = models.ImageField(upload_to="profiles/", blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Date joined")
    last_login = models.DateTimeField(auto_now=True, verbose_name="Last login")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "username"]

    objects = AccountManager()

    def __str__(self):
        return self.email

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.username

    @property
    def image(self):
        if self.profile_image:
            return self.profile_image.url
        return os.path.join(settings.STATIC_URL, "images", "default.webp")

    def has_perm(self, perm, obj=None):
        return self.is_staff

    def has_module_perms(self, app_label):
        return True

    # def get_absolute_url(self):
    #     return reverse('profile', args=[str(self.username)])
