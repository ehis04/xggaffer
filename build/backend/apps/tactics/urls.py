from rest_framework_nested.routers import NestedDefaultRouter

from apps.tactics.views import (
    TacticsBoardFrameViewSet,
    TacticsBoardItemViewSet,
    TacticsBoardViewSet,
)


def register_tactics_routes(clubs_router):
    clubs_router.register(
        r'tactics-boards',
        TacticsBoardViewSet,
        basename='club-tactics-board',
    )

    boards_router = NestedDefaultRouter(
        clubs_router,
        r'tactics-boards',
        lookup='board',
    )
    boards_router.register(
        r'frames',
        TacticsBoardFrameViewSet,
        basename='tactics-board-frame',
    )

    frames_router = NestedDefaultRouter(
        boards_router,
        r'frames',
        lookup='frame',
    )
    frames_router.register(
        r'items',
        TacticsBoardItemViewSet,
        basename='tactics-frame-item',
    )

    return [boards_router, frames_router]