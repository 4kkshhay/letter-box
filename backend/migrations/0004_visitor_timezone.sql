-- The visitor's own IANA timezone (from their browser) for each open and the
-- latest save, so the admin shows times as the visitor experienced them.
-- NULL for rows recorded before this column existed; shown in UTC.
ALTER TABLE page_opens ADD COLUMN tz TEXT;
ALTER TABLE page_state ADD COLUMN responded_tz TEXT;
