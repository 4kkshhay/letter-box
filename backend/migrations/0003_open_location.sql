-- Approximate, IP-derived location of each open as reported by Cloudflare's
-- visitor location headers. No IP address is stored. NULL when unavailable.
ALTER TABLE page_opens ADD COLUMN city TEXT;
ALTER TABLE page_opens ADD COLUMN region TEXT;
ALTER TABLE page_opens ADD COLUMN country TEXT;
