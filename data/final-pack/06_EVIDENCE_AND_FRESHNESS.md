# Evidence, Freshness and "Live" Semantics

## Field-level evidence coverage

Stop reporting only:

`offer has evidence = yes/no`

Report by critical field:

- input price
- output price
- free/economic mechanism
- quota value
- quota window/reset
- context
- tool support
- JSON support
- region
- requires card
- requires phone
- requires KYC
- automation allowed
- expiry
- endpoint availability
- throughput
- TTFT

Example:

```json
{
  "pricing": 0.91,
  "quota": 0.62,
  "context": 0.83,
  "tools": 0.54,
  "activation": 0.37,
  "endpoint_health": 0.21
}
```

## `live` definition

`/v1/deals/live` must not mean "some verification occurred recently."

It means that every claim necessary to assert the deal is currently actionable is fresh under its own policy.

Typical required fields:
- economic mechanism / price
- lifecycle
- promotion expiry if relevant
- quota conditions if relevant

Endpoint "live" is a different statement and should require recent endpoint probe evidence.

Use separate labels:
- `OFFER_CURRENT`
- `ENDPOINT_REACHABLE`
- `INFERENCE_VERIFIED`

## Negative observations

Parser/source failure is not evidence that an offer disappeared.

Record:
- source fetch failure
- empty parse
- schema drift
- explicit absence
as separate states.

## Value-weighted evidence program

Do not blindly chase a global 80% row coverage target.

Prioritize top economically useful routes.

Suggested:
- Top 100 critical routes: >=95% critical-field evidence coverage
- Next 400: >=75%
- Long tail: best-effort catalog

This maximizes actual user value.
