# Configuration-First - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- SECTION: principles -->
## Configuration-First Principles (All Roles)

### Core Rule
NO hardcoded values. ALL configuration comes from YAML.

### What Must Be Configurable
- Feature flags
- Thresholds and limits
- Timeouts and intervals
- API endpoints
- Credentials (via environment)
- Behavior toggles

### Benefits
- Change behavior without code changes
- Environment-specific settings
- Audit trail for configuration
- Easier testing (override config)

### Config Hierarchy
```
Default (code) → Core YAML → Pack YAML → Project YAML → Environment
```
Later layers override earlier ones.
<!-- /SECTION: principles -->

<!-- SECTION: check -->
## Configuration Validation (All Roles)

### Checklist
- [ ] No magic numbers in code
- [ ] No hardcoded strings for settings
- [ ] No hardcoded URLs or endpoints
- [ ] No hardcoded credentials
- [ ] Config loaded from YAML/environment
- [ ] Defaults documented

### Red Flags
🚩 **Immediate rejection:**
```pseudocode
// ❌ Hardcoded timeout
timeout = 5000

// ❌ Hardcoded URL
api_url = "https://api.example.com"

// ❌ Hardcoded threshold
if items.length > 100:
  paginate()
```

✅ **Correct pattern:**
```pseudocode
// ✅ From config
timeout = config.get("api.timeout")
api_url = config.get("api.baseUrl")
max_items = config.get("pagination.maxItems")
```

### Config File Structure
```yaml
# project.yaml
api:
  timeout: 5000
  baseUrl: https://api.example.com
  
pagination:
  maxItems: 100
  defaultPage: 1

features:
  enableNewDashboard: false
  betaUsers: []
```

### Environment Override
```yaml
# Secrets via environment
api:
  key: ${API_KEY}
  secret: ${API_SECRET}
```
<!-- /SECTION: check -->
