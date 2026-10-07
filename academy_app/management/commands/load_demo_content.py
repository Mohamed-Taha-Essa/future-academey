"""Load example homepage content so admins can see how each UI section looks.

Data: ``academy_app/demo_content/content.json`` (hero slides, services,
courses, course videos, reviews) and the files under
``academy_app/demo_content/media/``.

Safety rules:
* A model is only filled when its table is EMPTY — existing content is
  never changed, overwritten or duplicated. Safe to run more than once.
* Certificates, codes, contact messages and site settings are never touched.
* Records are created INACTIVE by default (hidden from the public site);
  pass ``--active`` to publish them.
* Files are uploaded to the default storage (R2 in production) only when
  missing, under the same name the records reference.
"""

import json
from pathlib import Path

from django.apps import apps
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction

DEMO_DIR = Path(__file__).resolve().parents[2] / "demo_content"
FILE_FIELDS = ("image", "video_file", "thumbnail")
# Parents before children (CourseVideo → Course).
MODEL_ORDER = (
    "academy_app.heroslide",
    "academy_app.service",
    "academy_app.course",
    "academy_app.coursevideo",
    "academy_app.review",
)


class Command(BaseCommand):
    help = "Load example homepage content into empty sections (inactive by default)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--active",
            action="store_true",
            help="Create the records as active (visible on the public site).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without writing anything.",
        )

    def handle(self, *args, active=False, dry_run=False, **options):
        records = json.loads((DEMO_DIR / "content.json").read_text(encoding="utf-8"))
        by_model = {label: [] for label in MODEL_ORDER}
        for record in records:
            if record["model"] in by_model:
                by_model[record["model"]].append(record)

        course_ids = {}  # demo pk → created Course pk
        with transaction.atomic():
            for label in MODEL_ORDER:
                model = apps.get_model(label)
                name = model._meta.verbose_name_plural
                if model.objects.exists():
                    self.stdout.write(f"- {label}: skipped ({name} already has data)")
                    continue
                created = 0
                for record in by_model[label]:
                    fields = dict(record["fields"])
                    fields.pop("created_at", None)
                    fields.pop("updated_at", None)
                    fields["is_active"] = active
                    if label == "academy_app.coursevideo":
                        course_id = course_ids.get(fields.pop("course"))
                        if course_id is None:
                            continue  # its course was not created by this run
                        fields["course_id"] = course_id
                    for field in FILE_FIELDS:
                        if fields.get(field) and not dry_run:
                            self._ensure_file(fields[field])
                    if dry_run:
                        if label == "academy_app.course":
                            course_ids[record["pk"]] = 0
                        created += 1
                        continue
                    obj = model.objects.create(**fields)
                    if label == "academy_app.course":
                        course_ids[record["pk"]] = obj.pk
                    created += 1
                self.stdout.write(f"+ {label}: {created} created")
            if dry_run:
                transaction.set_rollback(True)

        state = "ACTIVE (public)" if active else "inactive (hidden from the public site)"
        prefix = "Dry run — nothing written. " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}Demo content records: {state}."))

    def _ensure_file(self, name):
        if default_storage.exists(name):
            return
        source = DEMO_DIR / "media" / name
        with source.open("rb") as handle:
            stored = default_storage.save(name, File(handle))
        if stored != name:
            raise RuntimeError(f"Storage renamed {name} to {stored}")
        self.stdout.write(f"  uploaded {name}")
