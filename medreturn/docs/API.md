# API examples

Base URL in development: `http://localhost:8000/api`
Interactive docs: `http://localhost:8000/docs`

Every protected endpoint expects `Authorization: Bearer <token>`.

---

## Sign in

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"rhea","password":"medreturn123"}'
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1, "username": "rhea", "email": "rhea@demo.in",
    "full_name": "Rhea Sharma", "role": "household",
    "address": "Flat 204, Silver Oak Residency, Model Town, Ludhiana 141002"
  }
}
```

Save it:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"rhea","password":"medreturn123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

---

## Analyze a medicine image

```bash
curl -X POST http://localhost:8000/api/household/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@medicine.jpg"
```

```json
{
  "return_id": 5,
  "detected_item": "Tablet Strip",
  "category": "Tablet Strip",
  "confidence": 0.87,
  "confidence_threshold": 0.8,
  "eligibility_status": "ELIGIBLE",
  "inference_mode": "DEMO",
  "is_simulated": true,
  "model_version": "v1.2-demo",
  "message": "This looks like a supported return category. You can request a pickup.",
  "supported_categories": ["Tablet Strip", "Syrup Bottle", "Capsule Blister",
                           "Ointment Tube", "Inhaler", "Injection Vial"],
  "disclaimer": "This analysis assists with packaging identification only. It cannot determine whether a medicine is safe, genuine or legal from an image."
}
```

`inference_mode` is `DEMO` whenever no trained checkpoint is loaded. Treat
`is_simulated: true` as "do not present this as a real prediction".

Below the threshold you get `"eligibility_status": "NEEDS_REVIEW"` and a message
saying a person will check the item. The pickup can still be booked.

---

## Request a pickup

```bash
curl -X POST http://localhost:8000/api/household/pickups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "Flat 204, Silver Oak Residency, Model Town, Ludhiana 141002",
    "contact_phone": "+91 98150 44120",
    "preferred_date": "2026-09-20",
    "time_slot": "14:00-17:00",
    "item_count": 2,
    "approx_weight_kg": 0.25,
    "notes": "Leftover antibiotics.",
    "return_id": 5
  }'
```

```json
{
  "pickup_id": "MR-PU-2026-000005",
  "status": "REQUESTED",
  "preferred_date": "2026-09-20",
  "time_slot": "14:00-17:00",
  "item_count": 2,
  "approx_weight_kg": 0.25,
  "collector": null,
  "history": [{"status": "REQUESTED", "note": null, "created_at": "..."}]
}
```

---

## Track it

```bash
curl http://localhost:8000/api/household/pickups/MR-PU-2026-000005/tracking \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "pickup_id": "MR-PU-2026-000005",
  "status": "ON_THE_WAY",
  "demo": true,
  "collector_lat": 30.893, "collector_lng": 75.845,
  "destination_lat": 30.901, "destination_lng": 75.857,
  "eta_minutes": 9, "distance_km": 3.23,
  "note": "Demo tracking: simulated position, not a live GPS feed."
}
```

---

## Hospital: classify an item

```bash
curl -X POST http://localhost:8000/api/hospital/predict \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -F "file=@waste.jpg" -F "weight_kg=1.2" -F "location=Lab Inlet"
```

Accepted:

```json
{
  "event_id": "MR-WE-2026-000049",
  "predicted_class": "Sharps",
  "confidence": 0.94,
  "confidence_threshold": 0.8,
  "decision": "ACCEPTED",
  "route": "COMPARTMENT A",
  "reason": null,
  "inference_mode": "DEMO",
  "is_simulated": true,
  "hardware_simulated": true,
  "hardware_detail": "Hardware simulation: no physical gate is connected."
}
```

Below the threshold:

```json
{
  "event_id": "MR-WE-2026-000050",
  "predicted_class": "Glass",
  "confidence": 0.61,
  "decision": "QUARANTINED",
  "route": "QUARANTINE BAY",
  "reason": "Confidence 0.61 is below threshold 0.80"
}
```

An unsupported class is quarantined even at high confidence:
`"reason": "Predicted class is outside the configured supported list"`.

---

## Release a quarantined item

```bash
curl -X POST http://localhost:8000/api/hospital/quarantine/MR-QE-2026-00012/verify \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"release": true, "corrected_class": "Glass", "note": "Checked by hand."}'
```

The reviewer and timestamp are stored against the event. `"release": false`
keeps it held. There is no other way out of quarantine — nothing is released
automatically.

---

## Admin: drive a pickup to credits

```bash
# assign
curl -X POST http://localhost:8000/api/admin/pickups/MR-PU-2026-000005/assign \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" -d '{"collector_id": 1}'

# then one stage at a time
for S in ON_THE_WAY ARRIVED COLLECTED VERIFIED CREDITS_AWARDED COMPLETED; do
  curl -X PATCH http://localhost:8000/api/admin/pickups/MR-PU-2026-000005/status \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" -d "{\"status\": \"$S\"}"
done
```

Skipping a stage is rejected:

```json
{"detail": "Cannot move MR-PU-2026-000005 from ASSIGNED to COLLECTED. Next step is ON_THE_WAY."}
```

Replaying `CREDITS_AWARDED` does not pay twice — the transaction check and the
wallet row lock make the award idempotent.

---

## Errors

| Status | Meaning |
|---|---|
| 401 | Missing, invalid or expired token |
| 403 | Signed in, but the role is not allowed here |
| 404 | Not found, or belongs to someone else |
| 409 | Illegal state transition, or already reviewed |
| 413 | Upload over `MAX_UPLOAD_MB` |
| 415 | Not a JPG, PNG or WebP |
| 422 | Validation failure — see the `problems` array |
| 503 | Database down, or real inference required with no checkpoint |

Validation errors come back per-field:

```json
{
  "detail": "Please check the form.",
  "problems": ["address: String should have at least 10 characters"]
}
```
