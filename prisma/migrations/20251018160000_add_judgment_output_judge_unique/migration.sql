-- Add unique constraint for judgment output/judge combination
CREATE UNIQUE INDEX IF NOT EXISTS "judgments_outputId_judgeConfigId_key" ON "judgments"("outputId", "judgeConfigId");
