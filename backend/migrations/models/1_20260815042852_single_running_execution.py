"""Restricción "una sola ejecución RUNNING" (sección 11.4 / 13 del plan).

Lock del Orquestador (sección 8.2, decisión final sección 13/17/08): en vez
de un `pg_advisory_lock` de sesión, se apoya en esta unique index parcial
para que la propia base de datos rechace atómicamente una segunda fila
`executions(status='RUNNING')`, incluso bajo inserts concurrentes desde
procesos/workers distintos. Es el mecanismo definitivo, no interino: un
`pg_advisory_lock` encima sería redundante.
"""

from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE UNIQUE INDEX IF NOT EXISTS "uq_executions_single_running"
        ON "executions" ("status")
        WHERE "status" = 'RUNNING';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP INDEX IF EXISTS "uq_executions_single_running";"""
