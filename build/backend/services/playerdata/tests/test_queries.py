from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from apps.clubs.models import Club
from apps.playerdata.models import ClubSeasonEnrichment, PlayerSeasonEnrichment
from apps.players.models import ExternalProvider, Player
from services.playerdata.queries import (
    ClubSeasonEnrichmentRecord,
    PlayerSeasonEnrichmentRecord,
    get_club_season_enrichment,
    get_latest_club_enrichment,
    get_latest_player_enrichment,
    get_player_season_enrichment,
    list_enriched_club_players,
    list_enriched_clubs,
    list_enriched_players,
)

from datetime import datetime, timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from services.playerdata.queries import (
    ClubSeasonEnrichmentRecord,
    PlayerSeasonEnrichmentRecord,
    get_enriched_players,
)


class PlayerDataQueryPhase5ShapeTests(SimpleTestCase):
    def _player_record(self) -> PlayerSeasonEnrichmentRecord:
        return PlayerSeasonEnrichmentRecord(
            enrichment_id=101,
            player_id=7,
            player_name="Bukayo Saka",
            primary_position="RW",
            secondary_positions=["LW"],
            club_id=3,
            club_name="Arsenal",
            provider="understat",
            season_label="2024-2025",
            competition_code="EPL",
            competition_name="Premier League",
            matches_played=24,
            minutes_played=1950,
            goals=10,
            assists=6,
            shots=58,
            xg=Decimal("8.4"),
            xa=Decimal("7.2"),
            npg=Decimal("9"),
            npxg=Decimal("7.9"),
            key_passes=41,
            last_synced_at=datetime(2026, 3, 1, 12, 0, tzinfo=dt_timezone.utc),
            updated_at=datetime(2026, 3, 1, 12, 5, tzinfo=dt_timezone.utc),
        )

    def _club_record(self) -> ClubSeasonEnrichmentRecord:
        return ClubSeasonEnrichmentRecord(
            enrichment_id=201,
            club_id=3,
            club_name="Arsenal",
            provider="understat",
            season_label="2024-2025",
            competition_code="EPL",
            competition_name="Premier League",
            matches_played=27,
            wins=18,
            draws=6,
            losses=3,
            goals_for=52,
            goals_against=19,
            xg=Decimal("42.7"),
            xga=Decimal("21.3"),
            npxg=Decimal("39.9"),
            ppda=Decimal("8.8"),
            last_synced_at=datetime(2026, 3, 1, 12, 0, tzinfo=dt_timezone.utc),
            updated_at=datetime(2026, 3, 1, 12, 5, tzinfo=dt_timezone.utc),
        )

    def test_player_record_exposes_api_facing_properties(self):
        record = self._player_record()

        self.assertEqual(record.player["id"], 7)
        self.assertEqual(record.player["display_name"], "Bukayo Saka")
        self.assertEqual(record.club["name"], "Arsenal")
        self.assertEqual(record.context["provider"], "understat")
        self.assertEqual(record.context["season"], "2024-2025")
        self.assertEqual(record.key_metrics[0]["key"], "minutes_played")
        self.assertEqual(record.metrics[0]["key"], "matches_played")
        self.assertEqual(record.provider_coverage["provider"], "understat")
        self.assertTrue(record.has_summary_data)
        self.assertTrue(record.has_enrichment_data)
        self.assertEqual(record.missing_reasons, [])

    def test_player_record_explanation_snippet_is_stable(self):
        record = self._player_record()

        self.assertEqual(
            record.explanation_snippet,
            "24 matches, 1950 minutes, 10 goals, 6 assists.",
        )

    def test_club_record_exposes_api_facing_properties(self):
        record = self._club_record()

        self.assertEqual(record.club["id"], 3)
        self.assertEqual(record.context["competition_code"], "EPL")
        self.assertEqual(record.metrics[0]["key"], "matches_played")
        self.assertEqual(record.provider_coverage["matches_sampled"], 27)
        self.assertTrue(record.has_summary_data)
        self.assertEqual(record.missing_reasons, [])

    def test_get_enriched_players_returns_count_and_results_wrapper(self):
        mocked_results = [self._player_record(), self._player_record()]

        with patch(
            "services.playerdata.queries.list_enriched_players",
            return_value=mocked_results,
        ):
            payload = get_enriched_players(
                provider="understat",
                season="2024-2025",
                ordering="goals",
                limit=2,
            )

        self.assertEqual(payload["count"], 2)
        self.assertEqual(len(payload["results"]), 2)
        self.assertEqual(payload["results"][0].player["id"], 7)

def _choice_value(field: models.Field, preferred: str | None = None) -> str:
    choices = list(field.choices or [])
    if not choices:
        raise ValueError(f"Field {field.name} has no choices.")

    normalised_choices: list[str] = []
    for choice in choices:
        if isinstance(choice, (tuple, list)):
            normalised_choices.append(choice[0])
        else:
            normalised_choices.append(choice)

    if preferred and preferred in normalised_choices:
        return preferred

    return normalised_choices[0]


def _understat_provider() -> str:
    return getattr(ExternalProvider, "UNDERSTAT", None) or _choice_value(
        PlayerSeasonEnrichment._meta.get_field("provider")
    )


def _alternate_provider(primary: str) -> str:
    field = PlayerSeasonEnrichment._meta.get_field("provider")
    choices = list(field.choices or [])

    values: list[str] = []
    for choice in choices:
        if isinstance(choice, (tuple, list)):
            values.append(choice[0])
        else:
            values.append(choice)

    for value in values:
        if value != primary:
            return value

    return primary


def _required_model_kwargs(
    model_class: type[models.Model],
    *,
    sequence: int,
    user=None,
    overrides: dict | None = None,
) -> dict:
    overrides = overrides or {}
    kwargs: dict = {}

    for field in model_class._meta.concrete_fields:
        if getattr(field, "auto_created", False):
            continue
        if isinstance(field, models.AutoField):
            continue
        if field.name in overrides:
            kwargs[field.name] = overrides[field.name]
            continue
        if getattr(field, "has_default", lambda: False)():
            continue
        if field.null:
            continue
        if getattr(field, "blank", False):
            continue

        if field.is_relation:
            if field.related_model == get_user_model():
                if user is None:
                    raise ValueError(
                        f"Required relation {model_class.__name__}.{field.name} needs a user."
                    )
                kwargs[field.name] = user
                continue

            raise ValueError(
                f"Unhandled required relation {model_class.__name__}.{field.name}. "
                "Add it explicitly in overrides for this test."
            )

        if isinstance(field, models.EmailField):
            kwargs[field.name] = f"user{sequence}@example.com"
        elif isinstance(field, models.CharField):
            if field.choices:
                preferred = None
                if field.name == "visibility" and hasattr(model_class, "Visibility"):
                    preferred = getattr(model_class.Visibility, "PRIVATE", None)
                kwargs[field.name] = _choice_value(field, preferred=preferred)
            else:
                base_values = {
                    "name": f"Entity {sequence}",
                    "first_name": f"First{sequence}",
                    "last_name": f"Last{sequence}",
                    "display_name": f"Player {sequence}",
                    "city": "Dublin",
                    "country": "Ireland",
                    "stadium": f"Stadium {sequence}",
                    "division": "Premier",
                    "nationality": "Ireland",
                }
                value = base_values.get(field.name, f"{field.name}-{sequence}")
                kwargs[field.name] = value[: field.max_length]
        elif isinstance(field, models.TextField):
            kwargs[field.name] = f"{field.name} {sequence}"
        elif isinstance(field, models.BooleanField):
            kwargs[field.name] = False
        elif isinstance(field, models.DateField):
            kwargs[field.name] = date(2000, 1, min(sequence, 28))
        elif isinstance(field, models.DateTimeField):
            kwargs[field.name] = timezone.now()
        elif isinstance(field, models.DecimalField):
            kwargs[field.name] = Decimal("0.00")
        elif isinstance(
            field,
            (
                models.PositiveIntegerField,
                models.PositiveSmallIntegerField,
                models.IntegerField,
                models.SmallIntegerField,
                models.BigIntegerField,
            ),
        ):
            if field.name == "height_cm":
                kwargs[field.name] = 180
            else:
                kwargs[field.name] = sequence
        elif isinstance(field, models.JSONField):
            kwargs[field.name] = {}
        else:
            raise ValueError(
                f"Unhandled required field type for "
                f"{model_class.__name__}.{field.name}: {field.__class__.__name__}"
            )

    kwargs.update(overrides)
    return kwargs


def _create_user(*, sequence: int = 1):
    user_model = get_user_model()
    email = f"user{sequence}@example.com"

    create_kwargs = {}
    username_field = getattr(user_model, "USERNAME_FIELD", "username")
    create_kwargs[username_field] = email if username_field == "email" else f"user{sequence}"
    if hasattr(user_model, "email") and username_field != "email":
        create_kwargs["email"] = email

    manager = user_model.objects
    if hasattr(manager, "create_user"):
        return manager.create_user(password="Password123!", **create_kwargs)

    return manager.create(**create_kwargs)


def _create_club(*, user, sequence: int, name: str) -> Club:
    kwargs = _required_model_kwargs(
        Club,
        sequence=sequence,
        user=user,
        overrides={"name": name},
    )
    return Club.objects.create(**kwargs)


def _create_player(*, sequence: int, display_name: str, primary_position: str = "") -> Player:
    player = Player()

    field_names = {field.name for field in Player._meta.concrete_fields}

    defaults = {
        "first_name": f"First{sequence}",
        "last_name": f"Last{sequence}",
        "display_name": display_name,
    }

    for field_name, value in defaults.items():
        if field_name in field_names:
            setattr(player, field_name, value)

    if "primary_position" in field_names:
        field = Player._meta.get_field("primary_position")
        if primary_position:
            setattr(player, "primary_position", primary_position)
        elif field.choices:
            setattr(player, "primary_position", _choice_value(field))

    if "secondary_positions" in field_names:
        setattr(player, "secondary_positions", [])

    if "nationality" in field_names:
        # Player.nationality is ISO 3166-1 alpha-2 in model definition (max_length=2)
        setattr(player, "nationality", "IE")

    if "height_cm" in field_names:
        setattr(player, "height_cm", 180)

    if "date_of_birth" in field_names:
        setattr(player, "date_of_birth", date(2000, 1, min(sequence, 28)))

    player.save()
    return player


class PlayerDataQueryServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = _create_user(sequence=1)

        cls.understat_provider = _understat_provider()
        cls.other_provider = _alternate_provider(cls.understat_provider)

        cls.club_alpha = _create_club(user=cls.user, sequence=1, name="Alpha FC")
        cls.club_beta = _create_club(user=cls.user, sequence=2, name="Beta FC")

        cls.player_a = _create_player(
            sequence=1,
            display_name="Player A",
            primary_position="FW",
        )
        cls.player_b = _create_player(
            sequence=2,
            display_name="Player B",
            primary_position="MF",
        )
        cls.player_c = _create_player(
            sequence=3,
            display_name="Player C",
            primary_position="DF",
        )

        now = timezone.now()

        cls.player_a_2023 = PlayerSeasonEnrichment.objects.create(
            player=cls.player_a,
            club=cls.club_alpha,
            provider=cls.understat_provider,
            season_label="2023",
            competition_code="EPL",
            competition_name="Premier League",
            external_player_id="ua-2023",
            external_team_id="ta-2023",
            matches_played=22,
            minutes_played=1400,
            goals=9,
            assists=3,
            shots=30,
            xg=Decimal("8.40"),
            xa=Decimal("2.10"),
            npg=Decimal("8.00"),
            npxg=Decimal("7.90"),
            key_passes=12,
            last_synced_at=now - timedelta(days=10),
            metadata={"provider_notes": "hidden"},
            raw_snapshot={"raw": "hidden"},
        )

        cls.player_a_2024 = PlayerSeasonEnrichment.objects.create(
            player=cls.player_a,
            club=cls.club_alpha,
            provider=cls.understat_provider,
            season_label="2024",
            competition_code="EPL",
            competition_name="Premier League",
            external_player_id="ua-2024",
            external_team_id="ta-2024",
            matches_played=30,
            minutes_played=2200,
            goals=14,
            assists=7,
            shots=55,
            xg=Decimal("13.75"),
            xa=Decimal("6.20"),
            npg=Decimal("13.00"),
            npxg=Decimal("12.40"),
            key_passes=34,
            last_synced_at=now - timedelta(days=2),
            metadata={"provider_notes": "hidden"},
            raw_snapshot={"raw": "hidden"},
        )

        cls.player_a_other_provider = PlayerSeasonEnrichment.objects.create(
            player=cls.player_a,
            club=cls.club_beta,
            provider=cls.other_provider,
            season_label="2024",
            competition_code="UCL",
            competition_name="Champions League",
            external_player_id="oa-2024",
            external_team_id="ob-2024",
            matches_played=8,
            minutes_played=650,
            goals=2,
            assists=1,
            shots=14,
            xg=Decimal("2.20"),
            xa=Decimal("1.10"),
            npg=Decimal("2.00"),
            npxg=Decimal("1.90"),
            key_passes=5,
            last_synced_at=now - timedelta(days=1),
            metadata={"provider_notes": "hidden"},
            raw_snapshot={"raw": "hidden"},
        )

        cls.player_b_2024 = PlayerSeasonEnrichment.objects.create(
            player=cls.player_b,
            club=cls.club_alpha,
            provider=cls.understat_provider,
            season_label="2024",
            competition_code="EPL",
            competition_name="Premier League",
            external_player_id="ub-2024",
            external_team_id="tb-2024",
            matches_played=28,
            minutes_played=2050,
            goals=5,
            assists=11,
            shots=20,
            xg=Decimal("4.30"),
            xa=Decimal("8.40"),
            npg=Decimal("5.00"),
            npxg=Decimal("4.10"),
            key_passes=49,
            last_synced_at=now - timedelta(days=3),
            metadata={},
            raw_snapshot={},
        )

        cls.player_c_null_safe = PlayerSeasonEnrichment.objects.create(
            player=cls.player_c,
            club=None,
            provider=cls.understat_provider,
            season_label="2024",
            competition_code="EPL",
            competition_name="Premier League",
            external_player_id="uc-2024",
            external_team_id="",
            matches_played=6,
            minutes_played=190,
            goals=0,
            assists=0,
            shots=3,
            xg=None,
            xa=None,
            npg=None,
            npxg=None,
            key_passes=0,
            last_synced_at=None,
            metadata={"provider_notes": "hidden"},
            raw_snapshot={"raw": "hidden"},
        )

        cls.club_alpha_2023 = ClubSeasonEnrichment.objects.create(
            club=cls.club_alpha,
            provider=cls.understat_provider,
            season_label="2023",
            competition_code="EPL",
            competition_name="Premier League",
            external_team_id="club-alpha-2023",
            matches_played=38,
            wins=20,
            draws=8,
            losses=10,
            goals_for=61,
            goals_against=42,
            xg=Decimal("59.20"),
            xga=Decimal("41.80"),
            npxg=Decimal("55.10"),
            ppda=Decimal("10.40"),
            last_synced_at=now - timedelta(days=15),
            metadata={"provider_notes": "hidden"},
            raw_snapshot={"raw": "hidden"},
        )

        cls.club_alpha_2024 = ClubSeasonEnrichment.objects.create(
            club=cls.club_alpha,
            provider=cls.understat_provider,
            season_label="2024",
            competition_code="EPL",
            competition_name="Premier League",
            external_team_id="club-alpha-2024",
            matches_played=38,
            wins=24,
            draws=7,
            losses=7,
            goals_for=74,
            goals_against=33,
            xg=Decimal("71.80"),
            xga=Decimal("34.20"),
            npxg=Decimal("68.30"),
            ppda=Decimal("8.90"),
            last_synced_at=now - timedelta(days=2),
            metadata={"provider_notes": "hidden"},
            raw_snapshot={"raw": "hidden"},
        )

        cls.club_beta_2024 = ClubSeasonEnrichment.objects.create(
            club=cls.club_beta,
            provider=cls.other_provider,
            season_label="2024",
            competition_code="UCL",
            competition_name="Champions League",
            external_team_id="club-beta-2024",
            matches_played=12,
            wins=7,
            draws=2,
            losses=3,
            goals_for=19,
            goals_against=12,
            xg=Decimal("18.10"),
            xga=Decimal("11.50"),
            npxg=Decimal("16.60"),
            ppda=Decimal("11.70"),
            last_synced_at=now - timedelta(days=1),
            metadata={"provider_notes": "hidden"},
            raw_snapshot={"raw": "hidden"},
        )

    def test_get_player_season_enrichment_filters_by_exact_inputs(self):
        record = get_player_season_enrichment(
            self.player_a.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            club_id=self.club_alpha.id,
        )

        self.assertIsNotNone(record)
        self.assertIsInstance(record, PlayerSeasonEnrichmentRecord)
        self.assertEqual(record.player_id, self.player_a.id)
        self.assertEqual(record.club_id, self.club_alpha.id)
        self.assertEqual(record.provider, self.understat_provider)
        self.assertEqual(record.season_label, "2024")
        self.assertEqual(record.competition_code, "EPL")
        self.assertEqual(record.goals, 14)
        self.assertEqual(record.assists, 7)

    def test_get_latest_player_enrichment_prefers_most_recent_matching_record(self):
        record = get_latest_player_enrichment(
            self.player_a.id,
            provider=self.understat_provider,
            competition_code="EPL",
            club_id=self.club_alpha.id,
        )

        self.assertIsNotNone(record)
        self.assertEqual(record.season_label, "2024")
        self.assertEqual(record.minutes_played, 2200)

    def test_list_enriched_players_filters_by_player(self):
        records = list_enriched_players(player_id=self.player_b.id)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].player_id, self.player_b.id)
        self.assertEqual(records[0].player_name, "Player B")

    def test_list_enriched_players_filters_by_club(self):
        records = list_enriched_players(club_id=self.club_alpha.id, order_by="player_name", descending=False)

        self.assertEqual([record.player_name for record in records], ["Player A", "Player A", "Player B"])

    def test_list_enriched_players_filters_by_season_provider_and_competition(self):
        records = list_enriched_players(
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            order_by="goals",
            descending=True,
        )

        self.assertEqual([record.player_name for record in records], ["Player A", "Player B", "Player C"])
        self.assertEqual([record.goals for record in records], [14, 5, 0])

    def test_list_enriched_players_orders_by_goals_descending(self):
        records = list_enriched_players(
            season_label="2024",
            order_by="goals",
            descending=True,
        )

        self.assertEqual(records[0].player_name, "Player A")
        self.assertEqual(records[0].goals, 14)
        self.assertEqual(records[-1].player_name, "Player C")
        self.assertEqual(records[-1].goals, 0)

    def test_list_enriched_players_applies_metric_thresholds(self):
        records = list_enriched_players(
            season_label="2024",
            min_minutes=1000,
            min_goals=5,
            min_xg=Decimal("4.00"),
            order_by="goals",
            descending=True,
        )

        self.assertEqual([record.player_name for record in records], ["Player A", "Player B"])
        self.assertTrue(all(record.minutes_played >= 1000 for record in records))
        self.assertTrue(all(record.goals >= 5 for record in records))

    def test_list_enriched_club_players_wraps_club_filter_cleanly(self):
        records = list_enriched_club_players(
            self.club_alpha.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            order_by="assists",
            descending=True,
        )

        self.assertEqual([record.player_name for record in records], ["Player B", "Player A"])
        self.assertTrue(all(record.club_id == self.club_alpha.id for record in records))

    def test_null_safe_player_record_is_returned_honestly(self):
        record = get_player_season_enrichment(
            self.player_c.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
        )

        self.assertIsNotNone(record)
        self.assertIsNone(record.club_id)
        self.assertIsNone(record.club_name)
        self.assertIsNone(record.xg)
        self.assertIsNone(record.xa)
        self.assertIsNone(record.npg)
        self.assertIsNone(record.npxg)
        self.assertIsNone(record.last_synced_at)

    def test_player_query_returns_app_shaped_record_without_raw_payload_fields(self):
        record = get_player_season_enrichment(
            self.player_a.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
            club_id=self.club_alpha.id,
        )
        payload = record.to_dict()

        self.assertIn("player_id", payload)
        self.assertIn("player_name", payload)
        self.assertIn("club_name", payload)
        self.assertIn("xg", payload)
        self.assertNotIn("metadata", payload)
        self.assertNotIn("raw_snapshot", payload)
        self.assertNotIn("external_player_id", payload)
        self.assertNotIn("external_team_id", payload)

    def test_invalid_player_ordering_raises_value_error(self):
        with self.assertRaises(ValueError):
            list_enriched_players(order_by="unknown_metric")

    def test_get_club_season_enrichment_filters_by_exact_inputs(self):
        record = get_club_season_enrichment(
            self.club_alpha.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
        )

        self.assertIsNotNone(record)
        self.assertIsInstance(record, ClubSeasonEnrichmentRecord)
        self.assertEqual(record.club_id, self.club_alpha.id)
        self.assertEqual(record.club_name, "Alpha FC")
        self.assertEqual(record.provider, self.understat_provider)
        self.assertEqual(record.season_label, "2024")
        self.assertEqual(record.matches_played, 38)
        self.assertEqual(record.wins, 24)

    def test_get_latest_club_enrichment_prefers_most_recent_matching_record(self):
        record = get_latest_club_enrichment(
            self.club_alpha.id,
            provider=self.understat_provider,
            competition_code="EPL",
        )

        self.assertIsNotNone(record)
        self.assertEqual(record.season_label, "2024")
        self.assertEqual(record.goals_for, 74)

    def test_list_enriched_clubs_filters_and_orders(self):
        records = list_enriched_clubs(
            season_label="2024",
            order_by="matches_played",
            descending=True,
        )

        self.assertEqual([record.club_name for record in records], ["Alpha FC", "Beta FC"])

    def test_club_query_returns_app_shaped_record_without_raw_payload_fields(self):
        record = get_club_season_enrichment(
            self.club_alpha.id,
            season_label="2024",
            provider=self.understat_provider,
            competition_code="EPL",
        )
        payload = record.to_dict()

        self.assertIn("club_id", payload)
        self.assertIn("club_name", payload)
        self.assertIn("xg", payload)
        self.assertNotIn("metadata", payload)
        self.assertNotIn("raw_snapshot", payload)
        self.assertNotIn("external_team_id", payload)