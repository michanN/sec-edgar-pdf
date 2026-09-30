# Notes

## Scope and tradeoffs

A CLI is enough to select companies and save their reports. I left the API for later so I could spend the time on finding the right filing and getting a useful PDF. Docker was also deferred until the main flow worked.

Company names can be passed through `--companies`. Only the six supported names are accepted. Unknown names are rejected before any requests.

I know packages such as [sec-edgar](https://github.com/sec-edgar/sec-edgar) and [EdgarTools](https://github.com/dgunning/edgartools) already handle SEC integrations. Building a small client made the task more interesting and gives me decisions to explain. For production, I would compare those packages with maintaining our own client.

## Filing selection

### Company identifiers

Companies are identified by SEC CIKs, using a fixed name-to-CIK mapping for the six supported companies.

### What latest means

I select the newest exact `10-K` by filing date, then acceptance time if dates tie. Amendments are excluded. If the latest financial period matters more than submission order, I can switch to `reportDate` as the primary sort key.

### Recent and historical filings

The initial API check found the latest 10-K for all six companies in `filings.recent`. I will search that section only and report a clear error if no exact `10-K` is found. Historical submission files are outside the scope for now but could be added as a fallback if needed.

## SEC client

### Why sequential

Six companies don't need concurrency. Processing one at a time keeps the flow simple. If performance becomes a problem, I can add a worker pool with a shared rate limiter later.

### Rate limiting and retries

I will use PyrateLimiter for five requests per second and Stamina for bounded retries. This keeps the client small and saves time writing request handling. All sec edgar requests including assets and retries will share the same limiter.

I retry network failures, 429 and server errors up to three attempts in total. Stamina handles the waiting using `Retry-After` if sec edgar sends it as seconds or a date. I set a 60-second limit so the CLI doesn’t sit waiting for ages. If the delay is longer or we cant read it, we stop.

### Failure handling

A company-specific failure should not stop the other companies. Keep successful PDFs, report failures, and return a nonzero exit code if the run is incomplete. SEC access restrictions still stop the batch: a final 403/429 response or HTTP error with `Retry-After` must not be bypassed by moving to the next company.

## Downloading and conversion

### What to save

I would prefer saving the HTML and assets for easier debugging and reuse with another renderer. It also separates downloading from conversion. But finding all the assets and managing the files takes tim, so I have decided to go with only saving the PDF and accept fetching the content again when needed.

### Reusing/caching

After checking submissions for the latest 10-K, I reuse its PDF if the expected file exists. This avoids downloading assets and rendering again. Use `--refresh` to regenerate it. Files are validated when saved, so reuse skips validation. This simple file-based cache could later grow into a shared cache with explicit invalidation if needed.

The filename includes the company, accession number and renderer. A newer filing gets a different filename, so an older pdf will not stop it being generated.

### Renderer and interface

I chose Playwright as the baseline for Chromium's rendering of existing HTML and CSS. Apple's PDF looked good in manual testing; I haven't compared it with WeasyPrint yet. The shared `Converter` signature lets me swap and test renderers while reusing validation and saving.

### PDF validation

Check that the PDF opens, has pages, and contains extractable text. This doesn't prove completeness or visual quality. Later checks could cover images, key phrases, or AI-assisted review.

I validate a temporary PDF before replacing the final file. If conversion or validation fails, the existing PDF stays untouched.

I manually checked some of the generated pdfs and found:
- Goldman Sachs has a nearly blank page 2 with just a divider line. If I get time lets follow this up by investigating this further.

## Tests

Keep tests focused on getting the right report and reporting failures clearly. Use fake SEC data so tests stay offline.

### Unit tests
List of most important tests

- Select the latest exact `10-K` from unsorted metadata. Ignore amendments and break date ties using acceptance time. Check the selected document URL.
- Report clearly when no `10-K` exists.
- Recover from temporary request failures, stop after three attempts, and respect `Retry-After` within the wait limit. Use fake responses and no real waits.
- Reject unreadable PDFs and PDFs without pages or text.

### Integration tests

Run the CLI with real Chromium and fake SEC responses, without live network calls.

- Select a filing, fetch HTML and assets through the SEC client, render and validate the PDF, and check its filename, text, and logged save path. Keep only the final PDF.
- Fail clearly when an asset download fails, remove temporary output, and preserve any existing PDF.
- Reuse an existing pdf without fetching the report and regenerate it with the --refresh command.