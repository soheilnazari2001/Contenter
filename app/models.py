from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.cache import cache  # Django cache framework, Redis will be used as the backend


class BaseContentModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Content(BaseContentModel):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contents'
    )
    title = models.CharField(max_length=255, null=False)
    content = models.TextField()
    score_count_key = 'score_count:{}'
    score_sum_key = 'score_sum:{}'

    def update_score(self, new_score):
        redis_count_key = self.score_count_key.format(self.pk)
        redis_sum_key = self.score_sum_key.format(self.pk)
        cache.incr(redis_count_key)
        cache.incr(redis_sum_key, new_score)
        self._cache_average_score()
        self.save()

    def get_average_score(self):
        redis_count_key = self.score_count_key.format(self.pk)
        redis_sum_key = self.score_sum_key.format(self.pk)

        score_count = cache.get(redis_count_key)
        score_sum = cache.get(redis_sum_key)

        if score_count and score_sum:
            return score_sum / score_count
        content = Content.objects.get(pk=self.pk)
        return content.get_average_score_from_db()

    def get_average_score_from_db(self):
        if self.score_count > 0:
            return self.score_sum / self.score_count
        return 0.0

    def _cache_average_score(self):
        redis_count_key = self.score_count_key.format(self.pk)
        redis_sum_key = self.score_sum_key.format(self.pk)

        score_count = cache.get(redis_count_key)
        score_sum = cache.get(redis_sum_key)

        if score_count and score_sum:
            avg_score = score_sum / score_count
            cache.set(f'avg_score:{self.pk}', avg_score, timeout=3600)  # Cache avg score for 1 hour

    def __str__(self):
        return self.title


class Score(BaseContentModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scores')
    content = models.ForeignKey(Content, on_delete=models.CASCADE, related_name='scores')
    score = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(5)])

    class Meta:
        unique_together = ('user', 'content')

    def save(self, *args, **kwargs):
        if not self.pk:
            self.content.update_score(self.score)
        else:
            old_score = Score.objects.get(pk=self.pk).score
            score_delta = self.score - old_score
            self.content.update_score(score_delta)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} scored {self.score} for {self.content.title}"
