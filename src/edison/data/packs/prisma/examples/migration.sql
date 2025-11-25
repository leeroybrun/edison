-- Example migration
CREATE TABLE IF NOT EXISTS "Item" (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  "createdAt" timestamp with time zone DEFAULT now() NOT NULL
);

