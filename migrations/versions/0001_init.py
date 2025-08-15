from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tg_id", sa.BigInteger, nullable=False, unique=True, index=True),
        sa.Column("language", sa.String(8), server_default="ru"),
        sa.Column("referrer_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table("payments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, index=True, nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(18,8), nullable=False),
        sa.Column("currency", sa.String(12), nullable=False),
        sa.Column("external_id", sa.String(128), unique=True, nullable=False),
        sa.Column("status", sa.String(24), server_default="pending"),
        sa.Column("raw", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table("balances",
        sa.Column("user_id", sa.Integer, primary_key=True),
        sa.Column("amount", sa.Numeric(18,8), server_default="0"),
    )
    op.create_table("withdrawals",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, index=True, nullable=False),
        sa.Column("amount", sa.Numeric(18,8), nullable=False),
        sa.Column("address", sa.String(256), nullable=False),
        sa.Column("comment", sa.String(256)),
        sa.Column("status", sa.String(24), server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table("audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=True),
        sa.Column("event", sa.String(64)),
        sa.Column("data", sa.String(2048)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table("deposit_tags",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, index=True, nullable=False),
        sa.Column("tag", sa.String(32), nullable=False, unique=True, index=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table("state",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(512), nullable=False),
    )

def downgrade():
    op.drop_table("state")
    op.drop_table("deposit_tags")
    op.drop_table("audit_logs")
    op.drop_table("withdrawals")
    op.drop_table("balances")
    op.drop_table("payments")
    op.drop_table("users")
