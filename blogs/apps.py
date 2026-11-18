from django.apps import AppConfig


class BlogsConfig(AppConfig):
    name = 'blogs'

    def ready(self):
        from django.db.models.signals import post_delete, post_save
        from blogs.content_store import schedule_export
        from blogs.models import Blog, Post

        for model in (Blog, Post):
            post_save.connect(schedule_export, sender=model, dispatch_uid=f'content_export_save_{model.__name__}')
        post_delete.connect(schedule_export, sender=Post, dispatch_uid='content_export_delete_Post')
