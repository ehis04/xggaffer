from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.users.permissions import IsReferee
from .models import Law
from .serializers import CourseSectionSerializer

from apps.referee.progressTracking.services import (
    get_completed_item_ids,
    get_active_item_id,
)


class CourseDetailView(APIView):
    permission_classes = [IsAuthenticated, IsReferee]

    def get(self, request, law_number: int):
        up  = request.user.profile
        law = get_object_or_404(Law, law_number=law_number)

        completed_ids  = get_completed_item_ids(up, law)
        active_item_id = get_active_item_id(up, law)

        sections = law.sections.prefetch_related('items').order_by('order')

        serializer = CourseSectionSerializer(
            sections,
            many=True,
            context={
                'completed_ids':  completed_ids,
                'active_item_id': active_item_id,
            },
        )

        return Response({
            'law_number': law.law_number,
            'law_title':  law.title,
            'sections':   serializer.data,
        })