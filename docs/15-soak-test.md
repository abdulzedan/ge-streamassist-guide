# 15. Soak test

The harness in [`soak/`](../soak/README.md) runs checks from Cloud Run Jobs,
stores per-call timing and state, and renders Markdown, JSON and CSV reports.

It deliberately separates facts from estimates:

- `streamAssist` and `assist` calls are counted as candidate feature-query
  usage, not as a billing counter;
- native A2A calls are reported separately because the quota page does not map
  that endpoint to an Assistant-query unit;
- allowance math runs only when `SOAK_BILLING_MODEL` is `seat` or `legacy`;
- pay-as-you-go has no feature quota, while seat plans use pooled daily limits;
- the Usage & Spending page is the source of truth;
- `429` and `RESOURCE_EXHAUSTED` are recorded without guessing which quota fired.

For the current seat plans, Google lists 160 Assistant queries per Standard
licence per day and 200 per Plus licence per day, pooled by edition, project
and location. Most feature pools reset at midnight Pacific. Accounts that
received Google's August 17, 2026 billing-update email must use the legacy
quota page instead. Check the live quota page before setting the soak values.

The run record stores payload shape, sizes, states, invoked tool and skill
names, connector auth error counts, progress-update counts, planner markers,
`assistToken` and error categories. It does not store prompt text, answer text,
connector error text, bearer tokens or authorization URLs.

## completed Altostrat run

The existing 24-hour campaign ran from 2026-09-09 17:30Z to 2026-09-10
17:30Z:

| Measure | Result |
|---|---:|
| successful probes | 287 / 287 |
| API calls | 3,279 |
| candidate Assistant-query calls under the old counter | 799 |
| quota-like errors | 0 |
| missing five-minute slots | 4 |
| duplicate slots | 3 |

That campaign proved the base probe and the listed capability responses during
the window. It did not prove licence consumption. Its ADK/A2A StreamAssist
checks only required a successful text response, so they are not accepted as
routing proof; current Google documentation says those agent types are not
supported through StreamAssist.
