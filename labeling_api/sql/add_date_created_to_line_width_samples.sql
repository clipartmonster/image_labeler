-- Add date_created column to label_data.line_width_samples.
-- This table is unmanaged (managed = False in Django), so the column must
-- be added manually before deploying the matching model change.
--
-- Existing rows are back-filled with the current date via DEFAULT NOW().
-- New rows are populated by Django via auto_now_add=True on the model
-- field, with the DB DEFAULT as a safety net.

-- The model's db_table is the literal "label_data.line_width_samples"
-- (one identifier with a dot in the name, in the public schema), NOT
-- schema label_data + table line_width_samples. The quotes below are
-- therefore required.
ALTER TABLE "label_data.line_width_samples"
    ADD COLUMN IF NOT EXISTS date_created DATE NOT NULL DEFAULT NOW();
