# Generated manually: Season PK year -> id; FK rewrite for team/week; unique (league, year).

from django.db import migrations, models
import django.db.models.deletion


def _drop_fk_on_column(cursor, table, column):
    cursor.execute(
        """
        SELECT tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_catalog = kcu.constraint_catalog
         AND tc.constraint_schema = kcu.constraint_schema
         AND tc.constraint_name = kcu.constraint_name
        WHERE tc.table_schema = current_schema()
          AND tc.table_name = %s
          AND tc.constraint_type = 'FOREIGN KEY'
          AND kcu.column_name = %s
        """,
        [table, column],
    )
    for (name,) in cursor.fetchall():
        cursor.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT "{name}"')


def migrate_season_primary_key(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'postgresql':
        raise NotImplementedError(
            'Migration 0004_season_id_pk only supports PostgreSQL. '
            'Restore from backup or adapt SQL for your database.'
        )

    League = apps.get_model('main', 'League')
    Season = apps.get_model('main', 'Season')

    league = League.objects.order_by('pk').first()
    if league is None:
        league, _ = League.objects.get_or_create(
            slug='chatterbox-golf',
            defaults={'name': 'Chatterbox Golf'},
        )

    Season.objects.filter(league__isnull=True).update(league_id=league.pk)

    with connection.cursor() as cursor:
        for table in ('main_team', 'main_week'):
            _drop_fk_on_column(cursor, table, 'season_id')

        cursor.execute(
            """
            ALTER TABLE main_season ADD COLUMN id bigint;
            CREATE SEQUENCE IF NOT EXISTS main_season_id_seq;
            """
        )
        cursor.execute(
            """
            UPDATE main_season SET id = nextval('main_season_id_seq')
            WHERE id IS NULL;
            """
        )
        cursor.execute(
            """
            ALTER TABLE main_season ALTER COLUMN id SET NOT NULL;
            ALTER SEQUENCE main_season_id_seq OWNED BY main_season.id;
            ALTER TABLE main_season ALTER COLUMN id SET DEFAULT nextval('main_season_id_seq');
            """
        )

        cursor.execute(
            """
            UPDATE main_team AS t SET season_id = s.id
            FROM main_season AS s WHERE t.season_id = s.year;
            """
        )
        cursor.execute(
            """
            UPDATE main_week AS w SET season_id = s.id
            FROM main_season AS s WHERE w.season_id = s.year;
            """
        )

        cursor.execute(
            """
            SELECT conname FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'main_season' AND c.contype = 'p';
            """
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(f'ALTER TABLE main_season DROP CONSTRAINT "{row[0]}"')

        cursor.execute(
            """
            ALTER TABLE main_season ADD CONSTRAINT main_season_pkey PRIMARY KEY (id);
            """
        )

        cursor.execute(
            """
            SELECT setval(
                'main_season_id_seq',
                COALESCE((SELECT MAX(id) FROM main_season), 1)
            );
            """
        )

        cursor.execute(
            """
            ALTER TABLE main_season ALTER COLUMN league_id SET NOT NULL;
            """
        )

        cursor.execute(
            """
            ALTER TABLE main_season
            ADD CONSTRAINT season_unique_league_year UNIQUE (league_id, year);
            """
        )

        cursor.execute(
            """
            ALTER TABLE main_team ADD CONSTRAINT main_team_season_id_fkey
                FOREIGN KEY (season_id) REFERENCES main_season(id)
                ON DELETE CASCADE;
            """
        )
        cursor.execute(
            """
            ALTER TABLE main_week ADD CONSTRAINT main_week_season_id_fkey
                FOREIGN KEY (season_id) REFERENCES main_season(id)
                ON DELETE CASCADE;
            """
        )


def migrate_season_primary_key_reverse(apps, schema_editor):
    raise RuntimeError(
        'Reversing 0004_season_id_pk is not supported. Restore the database from a backup taken before this migration.'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_populate_season_flags'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    migrate_season_primary_key,
                    migrate_season_primary_key_reverse,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='season',
                    name='id',
                    field=models.BigAutoField(
                        auto_created=True,
                        null=True,
                        primary_key=False,
                        serialize=False,
                        verbose_name='ID',
                    ),
                    preserve_default=False,
                ),
                migrations.AlterField(
                    model_name='season',
                    name='year',
                    field=models.IntegerField(),
                ),
                migrations.AlterField(
                    model_name='season',
                    name='id',
                    field=models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                    preserve_default=False,
                ),
                migrations.AlterField(
                    model_name='season',
                    name='league',
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='seasons',
                        to='main.league',
                    ),
                ),
                migrations.AddConstraint(
                    model_name='season',
                    constraint=models.UniqueConstraint(
                        fields=('league', 'year'),
                        name='season_unique_league_year',
                    ),
                ),
            ],
        ),
    ]
