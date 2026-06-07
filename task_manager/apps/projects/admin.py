# task_manager/apps/projects/admin.py


from django.contrib import admin
from .models import Project
from apps.tasks.models import Task

class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ('name', 'status', 'priority', 'deadline')
    readonly_fields = ('name',)
    show_change_link = True

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    list_filter = ('user', 'created_at')
    search_fields = ('name',)
    inlines = [TaskInline]  