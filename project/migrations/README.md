# Enterprise upgrade migration

Apply `001_enterprise_upgrade.sql` to the Supabase PostgreSQL database before
enabling prompt, cost, or evaluation write APIs. It is additive and idempotent:
existing tables, API payloads, and data are not rewritten.

After applying it, regenerate the Python Prisma client from `project/`:

```powershell
prisma generate --schema schema.prisma
```

The trace read API continues to use the pre-existing `agent_logs` model, so it
remains available during a staged migration.
