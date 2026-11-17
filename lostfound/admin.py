from django.contrib import admin
from .models import Student, Item, Claim

# Register your models here.
admin.site.register(Student)

admin.site.register(Item)

admin.site.register(Claim)
