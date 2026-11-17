from django.db import models


# Create your models here.

class Student(models.Model):

    student_name = models.CharField(max_length=100)

    email = models.EmailField(unique=True)

    mobile_number = models.CharField(max_length=15)

    department = models.CharField(max_length=100)

    roll_number = models.CharField(max_length=20, unique=True)

    password = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return self.student_name


class Item(models.Model):

    ITEM_TYPE = [
        ('Lost', 'Lost'),
        ('Found', 'Found'),
    ]

    item_name = models.CharField(max_length=100)

    category = models.CharField(max_length=100)

    description = models.TextField()

    location = models.CharField(max_length=200)

    date = models.DateTimeField()

    item_type = models.CharField(
        max_length=10,
        choices=ITEM_TYPE
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE
    )

    status = models.CharField(
        max_length=20,
        default='Active'
    )
    image = models.ImageField(
        upload_to='items/',
        blank=True,
        null=True
)

    def __str__(self):
        return self.item_name


class Claim(models.Model):

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE
    )

    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE
    )

    claim_description = models.TextField()

    contact_number = models.CharField(max_length=15)

    claim_status = models.CharField(
        max_length=20,
        default='Pending'
    )

    lost_item_image = models.ImageField(
        upload_to='claims/',
        blank=True,
        null=True
    )

    lost_date = models.DateField(
        null=True,
        blank=True
    )

    lost_location = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    additional_details = models.TextField(
        blank=True,
        null=True
    )

    similarity_score = models.FloatField(
        null=True,
        blank=True
    )

    similarity_result = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    admin_note = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.student.student_name} - {self.item.item_name} ({self.claim_status})"
