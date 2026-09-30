# Notes

## Filing selection

### Recent and historical filings

The initial API check found the latest 10-K for all six companies in `filings.recent`. I will search that section only and report a clear error if no exact `10-K` is found. Historical submission files are outside the scope for now but could be added as a fallback if needed.

## Tests

Keep tests focused on getting the right report and reporting failures clearly. Use fake SEC data so tests stay offline.

### Unit tests
List of most important tests

- Select the latest exact `10-K` from unsorted metadata. Ignore amendments and break date ties using acceptance time. Check the selected document URL.
- Report clearly when no `10-K` exists.
