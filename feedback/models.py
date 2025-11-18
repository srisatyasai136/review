from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=15)

    def __str__(self):
        return self.user.get_full_name()

class Trainer(models.Model):
    name = models.CharField(max_length=100)
    expertise = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class DemoClass(models.Model):
    title = models.CharField(max_length=200)
    trainer = models.ForeignKey(Trainer, on_delete=models.CASCADE, related_name='demo_classes')
    date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} ({self.trainer.name})"


class Feedback(models.Model):
    RATING_CHOICES = [
        (1, '1 - Very poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]

    demo_class = models.ForeignKey(DemoClass, on_delete=models.CASCADE, related_name='feedbacks')
    student_name = models.CharField(max_length=100)
    student_email = models.EmailField()
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    liked_most = models.TextField( help_text="What did you like the most?")
    to_improve = models.TextField( help_text="What can be improved?")
    would_recommend = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(
        max_length=50,
        default="digital",
        help_text="Where this feedback came from (paper/digital/etc.)"
    )

    def __str__(self):
        return f"Feedback for {self.demo_class} - {self.rating} stars"
