# Error Handling - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: principles -->
## Error Handling Principles (All Roles)

### Core Rules
- All errors must be caught and handled appropriately
- User-facing errors must be meaningful (not stack traces)
- Async operations expose `loading`, `error`, `empty` states
- Errors are logged with context for debugging

### Error Categories
1. **Expected errors**: Validation, not found, unauthorized → Handle gracefully
2. **Unexpected errors**: Bugs, crashes → Log, report, fail safely
3. **External errors**: Network, third-party → Retry logic, fallbacks

### Fail-Closed Philosophy
When in doubt, fail closed. Better to halt than proceed with invalid state.
<!-- /section: principles -->

<!-- section: agent-implementation -->
## Error Handling Implementation (Agents)

### API/Service Layer
```pseudocode
function handle_request(request):
  try:
    validate_input(request)
    result = process(request)
    return success_response(result)
  catch ValidationError as e:
    return error_response(400, "Invalid input", e.details)
  catch NotFoundError as e:
    return error_response(404, "Not found", e.message)
  catch AuthError as e:
    return error_response(401, "Unauthorized")
  catch Exception as e:
    log_error(e, context=request)
    return error_response(500, "Internal error")
```

### UI/Component Layer
```pseudocode
function DataComponent({ data, isLoading, error }):
  if isLoading:
    return <LoadingSpinner />
  if error:
    return <ErrorState message={error.message} onRetry={refetch} />
  if data.length == 0:
    return <EmptyState message="No items" action={<CreateButton />} />
  return <DataList items={data} />
```

### Async Operations
- Always handle promise rejections
- Provide loading state while waiting
- Show meaningful error messages
- Offer retry when appropriate

### Logging
```pseudocode
// Include context for debugging
log_error(error, {
  user_id: current_user.id,
  request_id: request.id,
  operation: "process_payment",
  input: sanitized_input
})
```
<!-- /section: agent-implementation -->

<!-- section: validator-check -->
## Error Handling Validation (Validators)

### Checklist
- [ ] All async operations have error handling
- [ ] No swallowed errors (empty catch blocks)
- [ ] User errors are meaningful, not technical
- [ ] Error boundaries in UI components
- [ ] Loading states for async operations
- [ ] Retry logic where appropriate

### Red Flags
🚩 **Immediate rejection:**
- Empty catch blocks
- Stack traces shown to users
- No error handling on async operations
- Silent failures

🟡 **Needs review:**
- Generic error messages everywhere
- No retry logic for network operations
- Missing loading states
- Errors logged without context
<!-- /section: validator-check -->