from django.contrib import admin
from .Laws.models import Law, LawEdition, LawClause, LawChange, KeyConcept, ParsingJob
from .learningTools.models import Quiz, QuickDrill, TrueFalseAnswer, MCQOption, QuizQuestion
from .progressTracking.models import UserLearningProgress, QuizAttempt, DrillAttempt
from .profile.models import RefereeProfile

# Register your models here.

admin.site.register(Law)
admin.site.register(LawChange)
admin.site.register(LawEdition)
admin.site.register(LawClause)
admin.site.register(KeyConcept)
admin.site.register(ParsingJob)
admin.site.register(QuickDrill)
admin.site.register(Quiz)
admin.site.register(QuizQuestion)
admin.site.register(MCQOption)
admin.site.register(TrueFalseAnswer)
admin.site.register(UserLearningProgress)
admin.site.register(QuizAttempt)
admin.site.register(DrillAttempt)
admin.site.register(RefereeProfile)
