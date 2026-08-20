"""users: replace provider/provider_id with cognito_sub

The initial schema modeled OAuth identity as (provider, provider_id) for a
google/github design. Auth later moved to Amazon Cognito and the User model
now uses a single ``cognito_sub`` identifier, but the migration was never
regenerated — so staging Postgres was missing ``users.cognito_sub`` and every
sign-in failed at ``SELECT ... WHERE users.cognito_sub = ...``.

This reconciles the ``users`` table with the current model.

Revision ID: c3d9e1f2a4b5
Revises: a7f6a4fe33b1
Create Date: 2026-08-20 17:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d9e1f2a4b5'
down_revision: str | None = 'a7f6a4fe33b1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # New Cognito identifier. Safe as NOT NULL: sign-in has never succeeded, so
    # the users table is empty (users are only created during sign-in).
    op.add_column('users', sa.Column('cognito_sub', sa.String(length=128), nullable=False))
    op.create_unique_constraint('uq_users_cognito_sub', 'users', ['cognito_sub'])

    # Remove the old google/github provider identity.
    op.drop_constraint('uq_user_provider', 'users', type_='unique')
    op.drop_column('users', 'provider')
    op.drop_column('users', 'provider_id')
    op.execute('DROP TYPE IF EXISTS oauth_provider')


def downgrade() -> None:
    provider_enum = sa.Enum('google', 'github', name='oauth_provider')
    provider_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('users', sa.Column('provider', provider_enum, nullable=False))
    op.add_column('users', sa.Column('provider_id', sa.String(length=100), nullable=False))
    op.create_unique_constraint('uq_user_provider', 'users', ['provider', 'provider_id'])

    op.drop_constraint('uq_users_cognito_sub', 'users', type_='unique')
    op.drop_column('users', 'cognito_sub')
