# StorageBuddy API Documentation

## API Response Format

All API endpoints return a consistent, standardized response format.

### Success Response Structure

```json
{
  "success": true,
  "data": {
    "quests": [...]        // Actual response data nested under "data"
  },
  "message": "Optional message",
  "meta": {
    "timestamp": "2026-03-10T20:00:00Z",
    "version": "0.6.3"
  }
}
```

**Frontend Usage:**

```javascript
const response = await fetch('/api/active_quests');
const result = await response.json();
const quests = result.data.quests;  // Access via result.data.*
```

The `data` wrapper provides:
1. Clear separation between metadata and actual response content
2. Consistent structure across all endpoints
3. Easy error handling via `result.success` boolean

### Error Response Structure

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable message",
    "details": {}
  },
  "meta": {
    "timestamp": "2026-03-10T20:00:00Z",
    "version": "0.6.3"
  }
}
```

## Validation Patterns

### Recipe IDs

Recipe IDs are formatted as: `{skill}_{recipe_name}_{index}`

Example: `Alchemy_Bone Meal (from Any Bone)_0`

The validation pattern allows: `[\w\s\-\'",.()]+`
- Word characters (a-z, A-Z, 0-9, _)
- Spaces
- Hyphens
- Quotes (single and double)
- Commas, periods, parentheses

This is necessary because recipe names can contain:
- Parentheses: "Bone Meal (from Any Bone)"
- Quotes: "Aunt's Famous Pie"
- Numbers: "Healing Potion 2"

### Search Queries

- Maximum length: 200 characters
- Leading/trailing whitespace trimmed
- Empty queries allowed (returns empty results)

## Rate Limiting

All `/api/*` endpoints have rate limiting:
- 120 requests per minute sustained
- 20 requests per second burst limit

When rate limited, response returns HTTP 429:
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded. Please slow down.",
    "details": {
      "requests_last_minute": 121,
      "limit": 120,
      "retry_after": 5
    }
  }
}
```

## CORS Configuration

CORS is restricted to localhost only:
- `http://127.0.0.1:5000`
- `http://localhost:5000`

This is a local-only application. If browser extension support is needed, origins would need to be added.

## Security Headers

All responses include:
- `Content-Security-Policy` - Restricts script/style sources
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

## File Path Security

All file operations use path validation to prevent traversal attacks:
- Paths must resolve within allowed base directories
- Null bytes are rejected
- Maximum path length: 500 characters
- Maximum file size: 50MB (configurable)

## Endpoints Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/active_quests` | GET | List of active quests |
| `/api/completable_quests` | GET | Quests that can be turned in |
| `/api/purchasable_quests` | GET | Quests completable via vendors |
| `/api/quest/<name>` | GET | Quest checklist details |
| `/api/shopping_list` | GET/POST | Recipe shopping list |
| `/api/inventory` | GET | Full inventory data |
| `/api/skills` | GET | Character skills |
| `/api/favor` | GET | NPC favor levels |
| `/api/vendors` | GET | Vendor catalog |
| `/api/config_status` | GET | Configuration status |
| `/api/heartbeat` | POST | Keep-alive ping |
