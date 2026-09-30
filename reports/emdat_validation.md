# EM-DAT Validation Report (C21-2-FIX)

## Summary
Disaster events for power sector assessment (Drought, Flood, Extreme Temperature, Storm) across three countries.

## Event Counts

| Country | Total Events |
|---|---|
| BRA | 239 |
| IND | 622 |
| PRT | 38 |

## Event Types

- Flood: 525
- Storm: 252
- Extreme temperature: 80
- Drought: 42

## Coverage
- Earliest event: 1900
- Latest event: 2024
- Total rows: 899
- Schema: country | event_type | start_year | end_year | deaths | affected | economic_damage
  (Note: economic_damage is in thousands USD)

## Validation Status
- No duplicate event IDs (DisNo.): Not checked (IDs not retained in filtered output)
- All 3 countries present: Yes
- Disaster types filtered: ['Drought', 'Extreme temperature', 'Flood', 'Storm']
- Status: PASS
