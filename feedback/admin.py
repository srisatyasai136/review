from django.contrib import admin
from .models import Trainer, DemoClass, Feedback


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ('name', 'expertise', 'email')
    # pass
    search_fields = ('name', 'expertise')


@admin.register(DemoClass)
class DemoClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'trainer', 'date', 'duration_minutes', 'is_active')
    list_filter = ('trainer', 'is_active')
    search_fields = ('title',)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('student_name','demo_class', 'rating', 'would_recommend', 'created_at')
    list_filter = ('rating', 'would_recommend', 'demo_class__trainer')
    search_fields = ('student_name', 'student_email', 'liked_most', 'to_improve')
    date_hierarchy = 'created_at'
