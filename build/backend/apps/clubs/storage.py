import os
import posixpath
import re
import uuid

from django.conf import settings

from .models import ClubResource

try:
    import cloudinary
    import cloudinary.uploader
    import cloudinary.utils
except ImportError:  # pragma: no cover
    cloudinary = None


class ClubResourceStorageError(Exception):
    pass


def cloudinary_resources_enabled():
    return bool(
        getattr(settings, 'CLUB_RESOURCES_USE_CLOUDINARY', False) and
        getattr(settings, 'CLOUDINARY_CLOUD_NAME', '') and
        getattr(settings, 'CLOUDINARY_API_KEY', '') and
        getattr(settings, 'CLOUDINARY_API_SECRET', '')
    )


def _require_cloudinary():
    if cloudinary is None:
        raise ClubResourceStorageError(
            'Cloudinary SDK is not installed. Install the cloudinary package first.'
        )

    if not cloudinary_resources_enabled():
        raise ClubResourceStorageError(
            'Cloudinary resource storage is not enabled or is missing required credentials.'
        )


def _configure_cloudinary():
    _require_cloudinary()

    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def _slugify_stem(filename):
    stem, _ = os.path.splitext(filename or '')
    normalised = re.sub(r'[^A-Za-z0-9_-]+', '-', stem).strip('-_').lower()
    return normalised or 'resource'


def get_cloudinary_resource_type(file_kind):
    if file_kind == ClubResource.FileKind.IMAGE:
        return 'image'
    return 'raw'


def build_club_resource_public_id(club_id, original_filename):
    safe_stem = _slugify_stem(original_filename)
    unique_suffix = uuid.uuid4().hex[:12]

    return posixpath.join(
        settings.CLUB_RESOURCES_CLOUDINARY_FOLDER.rstrip('/'),
        f'club_{club_id}',
        f'{unique_suffix}_{safe_stem}',
    )


def upload_club_resource_to_cloudinary(*, uploaded_file, club_id, file_kind, original_filename):
    _configure_cloudinary()

    resource_type = get_cloudinary_resource_type(file_kind)
    public_id = build_club_resource_public_id(club_id, original_filename)

    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)

    try:
        upload_result = cloudinary.uploader.upload(
            uploaded_file,
            public_id=public_id,
            resource_type=resource_type,
            type='authenticated',
            overwrite=False,
            use_filename=False,
            unique_filename=False,
            invalidate=False,
        )
    except Exception as exc:  # pragma: no cover
        raise ClubResourceStorageError(f'Cloudinary upload failed: {exc}') from exc
    finally:
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)

    return {
        'storage_backend': ClubResource.StorageBackend.CLOUDINARY,
        'storage_key': upload_result['public_id'],
    }


def build_cloudinary_signed_delivery_url(resource):
    _configure_cloudinary()

    if resource.storage_backend != ClubResource.StorageBackend.CLOUDINARY:
        raise ClubResourceStorageError('Resource is not stored in Cloudinary.')

    if not resource.storage_key:
        raise ClubResourceStorageError('Cloudinary storage_key is missing for this resource.')

    resource_type = get_cloudinary_resource_type(resource.file_kind)
    extension = resource.get_extension() or None

    if extension and resource.storage_key.endswith(f'.{extension}'):
        extension = None

    try:
        signed_url, _ = cloudinary.utils.cloudinary_url(
            resource.storage_key,
            resource_type=resource_type,
            type='authenticated',
            sign_url=True,
            secure=True,
            format=extension,
        )
    except Exception as exc:  # pragma: no cover
        raise ClubResourceStorageError(
            f'Could not build Cloudinary signed delivery URL: {exc}'
        ) from exc

    return signed_url