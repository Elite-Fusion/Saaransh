# Saaransh AI — Investigation Report Prompt

> **Phase 6 — Feature.** Generates comprehensive investigation reports for crime analysis queries.

---

## Task

You are generating an investigation report based on crime data analysis. Your job is to produce a structured report that includes all the key metrics and insights an investigating officer would need for the specified crime type, location, and time period.

---

## Inputs

The prompt is rendered with the following variables:

- `{{QUESTION}}` — the officer's original natural-language question.
- `{{STATISTICS}}` — JSON object containing basic statistics (total, solved, pending, etc.)
- `{{HOTSPOTS}}` — JSON array of location objects with case counts, sorted by frequency
- `{{TIME_ANALYSIS}}` — JSON object containing time-of-day and day-of-week patterns
- `{{REPEAT_OFFENDERS}}` — JSON array of repeat offender information
- `{{TREND_DATA}}` — JSON array showing crime trends over time
- `{{PREDICTIONS}}` — JSON object with forecasted values
- `{{DEMOGRAPHICS}}` — JSON object with victim/accused demographics if relevant
- `{{CASE_SAMPLES}}` — JSON array of representative case examples

---

## Output format

Return a JSON object shaped exactly like this:

```json
{
  "headline": "One-sentence summary of the key finding.",
  "summary": "Brief 2-3 sentence overview of the situation.",
  "metrics": {
    "total": <integer>,
    "solved": <integer>,
    "pending": <integer>,
    "arrests": <integer>,
    "confidence": "<percentage>%"
  },
  "reasoning": [
    "<brief explanation of data sources and methodology>",
    "<explanation of how the location was determined>",
    "<explanation of how the time period was determined>",
    "<any data quality notes or limitations>"
  ],
  "hotspots": [
    {"rank": 1, "name": "<location name>", "count": <integer>},
    {"rank": 2, "name": "<location name>", "count": <integer>},
    {"rank": 3, "name": "<location name>", "count": <integer>}
  ],
  "mostActiveTime": "<time range> (<count> cases)",
  "repeatOffendersCount": <integer>,
  "trend": "<improving/deteriorating/stable> (<percentage>% change)",
  "prediction": "<predicted count for next period>",
  "suggestedDeployment": "<specific recommendation for resource allocation>",
  "confidence": "<high/medium/low>"
}
```

## Rules

- `headline` is a single sentence. If data is insufficient, state the limitation clearly.
- `summary` provides context and key insights in 2-3 sentences.
- All numeric values must be integers unless otherwise specified.
- `reasoning` is an array of brief explanations (1-2 sentences each) about the analysis process.
- `hotspots` lists the top 3 locations by case count, ranked 1-3.
- `mostActiveTime` specifies the time period with highest activity and the case count.
- `repeatOffendersCount` is the number of individuals linked to multiple cases.
- `trend` describes the direction and percentage change compared to previous period.
- `prediction` estimates the expected number for the next similar time period.
- `suggestedDeployment` provides a concrete, actionable recommendation for law enforcement.
- `confidence` reflects the overall reliability of the analysis based on data quality and completeness.

## Data Quality and Limitations

- If data is incomplete for any section, state this clearly in the relevant field.
- Never invent or guess data values that are not supported by the analysis.
- If confidence is low due to limited data, explain what additional information would improve the analysis.