"""production signup: email, license, verification columns and invite codes

Revision ID: e4f2a8b1c9d0
Revises: 9f3e2a1b7c4d
Create Date: 2026-09-24 12:00:00.000000

"""

import contextlib
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4f2a8b1c9d0"
down_revision: Union[str, Sequence[str], None] = "9f3e2a1b7c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_names() -> set[str]:
    from sqlalchemy import inspect

    return set(inspect(op.get_bind()).get_table_names())


def _table_columns(table_name: str) -> set[str]:
    from sqlalchemy import inspect

    return {c["name"] for c in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    tables = _table_names()
    if "invite_codes" not in tables:
        op.create_table(
            "invite_codes",
            sa.Column("code", sa.String(), primary_key=True),
            sa.Column("clinic_code", sa.String(), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(), server_default=""),
            sa.Column("created_at", sa.String(), nullable=False, server_default=""),
            sa.Column("expires_at", sa.String(), server_default=""),
            sa.Column("max_uses", sa.Integer(), server_default="1"),
            sa.Column("use_count", sa.Integer(), server_default="0"),
            sa.Column("active", sa.Integer(), server_default="1"),
            sa.Column("used_by", sa.String(), server_default=""),
        )
    if "patient_profiles" in tables:
        cols = _table_columns("patient_profiles")
        with contextlib.suppress(Exception):
            if "email" not in cols:
                op.add_column("patient_profiles", sa.Column("email", sa.String(), server_default="", nullable=True))
        with contextlib.suppress(Exception):
            if "license_number" not in cols:
                op.add_column(
                    "patient_profiles", sa.Column("license_number", sa.String(), server_default="", nullable=True)
                )
        with contextlib.suppress(Exception):
            if "email_verified_at" not in cols:
                op.add_column(
                    "patient_profiles", sa.Column("email_verified_at", sa.String(), server_default="", nullable=True)
                )
        with contextlib.suppress(Exception):
            if "verification_token" not in cols:
                op.add_column(
                    "patient_profiles", sa.Column("verification_token", sa.String(), server_default="", nullable=True)
                )
        with contextlib.suppress(Exception):
            if "verification_expires" not in cols:
                op.add_column(
                    "patient_profiles", sa.Column("verification_expires", sa.String(), server_default="", nullable=True)
                )


def downgrade() -> None:
    tables = _table_names()
    if "patient_profiles" in tables:
        cols = _table_columns("patient_profiles")
        with contextlib.suppress(Exception):
            for col in ("verification_expires", "verification_token", "email_verified_at", "license_number", "email"):
                if col in cols:
                    op.drop_column("patient_profiles", col)
    if "invite_codes" in tables:
        with contextlib.suppress(Exception):
            op.drop_table("invite_codes")
