# learningTools/models.py
#
# Scenario and drill content is stored directly on laws.CourseItem as JSON
# payload fields — no separate models are needed for those activity types.
#
# This file is reserved for the standalone Quiz model, which will be
# implemented when the quiz module is built out. At that point, CourseItem.quiz_id
# will become a ForeignKey to Quiz rather than a plain CharField.