from rest_framework_nested.routers import NestedDefaultRouter

from .views import TrainingBlockViewSet, TrainingSessionPlayerViewSet, TrainingSessionViewSet


def register_training_routes(clubs_router):
    clubs_router.register(
        r'training-sessions',
        TrainingSessionViewSet,
        basename='club-training-session',
    )

    sessions_router = NestedDefaultRouter(
        clubs_router,
        r'training-sessions',
        lookup='session',
    )
    sessions_router.register(
        r'blocks',
        TrainingBlockViewSet,
        basename='training-session-block',
    )
    sessions_router.register(
        r'players',
        TrainingSessionPlayerViewSet,
        basename='training-session-player',
    )

    return [sessions_router]
