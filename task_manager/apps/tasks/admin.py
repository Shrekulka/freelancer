# task_manager/apps/tasks/admin.py

from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'priority', 'deadline')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('name', 'description')
