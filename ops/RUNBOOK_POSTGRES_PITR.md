# Postgres PITR Runbook (Patroni)

1. Preconditions
- WAL archiving enabled (archive_mode=on, wal-g configured)
- Backups visible at S3 path in `S3_BUCKET/pg`

2. Take note of target timestamp
- Record target timestamp (UTC) to restore to

3. Spin up restore environment
- Create a new namespace or use staging
- Deploy Patroni StatefulSet with `PATRONI_POSTGRESQL_DATA_DIR=/data/pgdata-restore`
- Mount empty PVCs; scale replicas to 1 for speed

4. Initialize from base backup
- Exec into pod and run:
```
wal-g backup-list
wal-g backup-fetch /data/pgdata-restore LATEST
```

5. Configure recovery target
- Create `recovery.signal` and `postgresql.auto.conf` entries:
```
echo "recovery_target_time='2025-01-01 00:00:00+00'" >> /data/pgdata-restore/postgresql.auto.conf
echo "restore_command='wal-g wal-fetch %f %p'" >> /data/pgdata-restore/postgresql.auto.conf
```
- Ensure ownership/permissions match Postgres user

6. Start Postgres
- Restart Patroni pod; verify logs show WAL replay

7. Validate
- Connect to DB; run smoke queries (select counts, table presence)

8. Cutover plan (if needed)
- Scale down primary; re-point `DATABASE_URL` to restored service
- Coordinate app downtime and run health checks

9. Cleanup
- Tear down restore environment after validation