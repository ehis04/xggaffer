from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from .widget_payload import (
	WidgetConfidenceSerializer,
	WidgetFreshnessSerializer,
	WidgetPayloadSerializer,
)


_LEGACY_SERIALIZERS_PATH = Path(__file__).resolve().parent.parent / 'serializers.py'
_SPEC = spec_from_file_location('apps.predictions._legacy_serializers', _LEGACY_SERIALIZERS_PATH)

if _SPEC is None or _SPEC.loader is None:
	raise ImportError(f'Could not load legacy serializers module: {_LEGACY_SERIALIZERS_PATH}')

_LEGACY_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_LEGACY_MODULE)

# Re-export serializer classes defined in apps/predictions/serializers.py
for _name, _value in vars(_LEGACY_MODULE).items():
	if _name.endswith('Serializer'):
		globals()[_name] = _value

__all__ = [
	name
	for name in globals()
	if name.endswith('Serializer')
]
