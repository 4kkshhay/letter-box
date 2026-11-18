-- How the browser loaded the page for each open: navigate, reload or
-- back_forward. NULL for opens recorded before this column existed.
ALTER TABLE page_opens ADD COLUMN kind TEXT;
