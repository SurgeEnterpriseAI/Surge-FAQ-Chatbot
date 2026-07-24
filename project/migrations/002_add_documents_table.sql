-- Migration: Add documents table and document_id reference on parent_chunks

CREATE TABLE IF NOT EXISTS "documents" (
    "id" TEXT NOT NULL,
    "filename" TEXT NOT NULL,
    "chunk_count" INTEGER NOT NULL DEFAULT 0,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "metadata" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "documents_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX IF NOT EXISTS "documents_filename_key" ON "documents"("filename");

ALTER TABLE "parent_chunks" ADD COLUMN IF NOT EXISTS "document_id" TEXT;

CREATE INDEX IF NOT EXISTS "parent_chunks_document_id_idx" ON "parent_chunks"("document_id");

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'parent_chunks_document_id_fkey'
    ) THEN
        ALTER TABLE "parent_chunks"
        ADD CONSTRAINT "parent_chunks_document_id_fkey"
        FOREIGN KEY ("document_id") REFERENCES "documents"("id")
        ON DELETE SET NULL ON UPDATE CASCADE;
    END IF;
END $$;
