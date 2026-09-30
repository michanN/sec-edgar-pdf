# Notes

## Filing selection

### Recent and historical filings

The initial API check found the latest 10-K for all six companies in `filings.recent`. I will search that section only and report a clear error if no exact `10-K` is found. Historical submission files are outside the scope for now but could be added as a fallback if needed.

## SEC client

### Rate limiting and retries

I will use PyrateLimiter for five requests per second and Stamina for bounded retries. This keeps the client small and saves time writing request handling. All sec edgar requests including assets and retries will share the same limiter.

I retry network failures, 429 and server errors up to three attempts in total. Stamina handles the waiting using `Retry-After` if sec edgar sends it as seconds or a date. I set a 60-second limit so the CLI doesn’t sit waiting for ages. If the delay is longer or we cant read it, we stop.

## Downloading and conversion

### What to save

I would prefer saving the HTML and assets for easier debugging and reuse with another renderer. It also separates downloading from conversion. But finding all the assets and managing the files takes tim, so I have decided to go with only saving the PDF and accept fetching the content again when needed.

## Tests

Keep tests focused on getting the right report and reporting failures clearly. Use fake SEC data so tests stay offline.

### Unit tests
List of most important tests

- Select the latest exact `10-K` from unsorted metadata. Ignore amendments and break date ties using acceptance time. Check the selected document URL.
- Report clearly when no `10-K` exists.
