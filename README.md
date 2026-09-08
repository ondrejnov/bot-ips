# bot-ips

**Official crawler IP ranges, collected into one JSON snapshot and one plain-text list.**

`bot-ips` downloads the IP ranges published by search engines, AI services, and
other crawlers. It validates each source, preserves per-bot provenance, and
produces a deduplicated aggregate for log analysis and CIDR-aware integrations.

Python 3.10+ · Standard library only · IPv4 and IPv6 · GitHub Actions automation

[Quick Start](#quick-start) | [Sources](#sources) | [Output Formats](#output-formats) | [Automation](#automation) | [Testing](#testing)

## Quick Start

From the project directory:

```bash
python3 bot_ips.py
```

No packages, API keys, or account setup are required for the bundled sources.
You need Python 3.10 or newer, HTTPS access to the providers, and write access to
the output directory.

Each successful run generates both files:

| File | Contents |
| --- | --- |
| `data/bot-ips.json` | Per-bot ranges, source URLs, timestamps, and merged IPv4/IPv6 lists |
| `data/bot-ips.txt` | All merged ranges, one CIDR per line, with no header |

The output directory is created automatically. Both generated files are tracked
in Git and updated automatically by GitHub Actions.

> [!IMPORTANT]
> Both formats contain **CIDR ranges**, not expanded individual IP addresses.
> A single IPv6 range can contain an impractically large number of addresses.
> Use CIDR containment, not string equality, when matching a request IP.

## Sources

The default configuration in [`sources.json`](sources.json) contains 18 feeds:

| Bot ID | Provider / Bot | Official Feed |
| --- | --- | --- |
| `googlebot` | Googlebot | [googlebot.json](https://developers.google.com/search/apis/ipranges/googlebot.json) |
| `google-special-crawlers` | Google / Special-case crawlers (such as AdsBot) | [special-crawlers.json](https://developers.google.com/static/crawling/ipranges/special-crawlers.json) |
| `google-user-triggered-fetchers` | Google / User-controlled fetchers | [user-triggered-fetchers.json](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers.json) |
| `google-user-triggered-fetchers-google` | Google / Google-controlled user-triggered fetchers | [user-triggered-fetchers-google.json](https://developers.google.com/static/crawling/ipranges/user-triggered-fetchers-google.json) |
| `google-user-triggered-agents` | Google / User-triggered agents (Google-Agent) | [user-triggered-agents.json](https://developers.google.com/static/crawling/ipranges/user-triggered-agents.json) |
| `applebot` | Apple / Applebot | [applebot.json](https://search.developer.apple.com/applebot.json) |
| `seznambot` | Seznam.cz / SeznamBot | [seznambot.json](https://search.seznam.cz/ipranges/seznambot.json) |
| `bingbot` | Bingbot | [bingbot.json](https://www.bing.com/toolbox/bingbot.json) |
| `claude` | Anthropic / Claude | [bots.json](https://claude.com/crawling/bots.json) |
| `chatgpt-user` | OpenAI / ChatGPT-User | [chatgpt-user.json](https://openai.com/chatgpt-user.json) |
| `searchbot` | OpenAI / SearchBot | [searchbot.json](https://openai.com/searchbot.json) |
| `gptbot` | OpenAI / GPTBot | [gptbot.json](https://openai.com/gptbot.json) |
| `ahrefs` | Ahrefs | [crawler-ip-ranges](https://api.ahrefs.com/v3/public/crawler-ip-ranges) |
| `duckduckbot` | DuckDuckGo / DuckDuckBot | [duckduckbot.json](https://duckduckgo.com/duckduckbot.json) |
| `duckassistbot` | DuckDuckGo / DuckAssistBot | [duckassistbot.json](https://duckduckgo.com/duckassistbot.json) |
| `ccbot` | Common Crawl / CCBot | [ccbot.json](https://index.commoncrawl.org/ccbot.json) |
| `perplexitybot` | PerplexityBot | [perplexitybot.json](https://www.perplexity.ai/perplexitybot.json) |
| `perplexity-user` | Perplexity-User | [perplexity-user.json](https://www.perplexity.ai/perplexity-user.json) |

The original 12 URLs were discovered through [adver.tools/bot-ips](https://adver.tools/bot-ips/).
The additional feeds are documented by [Apple](https://support.apple.com/en-us/119829),
[Seznam](https://o-seznam.cz/napoveda/vyhledavani/en/seznambot-crawler/), and
[Google](https://developers.google.com/crawling/docs/crawlers-fetchers/verify-google-requests).
All feeds were directly checked on September 8, 2026. The program does **not**
scrape these documentation pages or download data from adver.tools at runtime;
it fetches the configured feeds directly.

Google's supplemental feeds remain separate from `googlebot`. User-triggered
fetchers generally ignore `robots.txt`, and the user-controlled feed includes
fetches from applications hosted on Google Cloud, not just Google's own products.
Do not treat these ranges as an automatic Googlebot allowlist. Use per-bot JSON
entries when selecting trusted categories; the combined TXT includes all feeds.

Coverage is limited to those feeds. This is not an exhaustive directory of all
crawlers, all Google services, or all infrastructure owned by each provider.

## Usage

```bash
# Generate both files in the default data directory.
python3 bot_ips.py

# Generate /tmp/crawlers.json and /tmp/crawlers.txt.
python3 bot_ips.py --output /tmp/crawlers.json

# Use a custom source configuration and socket timeout.
python3 bot_ips.py --sources custom-sources.json --timeout 20

# Display CLI help.
python3 bot_ips.py --help
```

| Option | Default | Behavior |
| --- | --- | --- |
| `--sources PATH` | `sources.json` beside the script | JSON object mapping bot IDs to HTTPS feed URLs |
| `--output PATH` | `data/bot-ips.json` beside the script | JSON destination; must end in `.json`. A sibling `.txt` file is always generated |
| `--timeout SECONDS` | `30` | Positive, finite socket timeout; not a deadline for the entire run |
| `-h`, `--help` | | Print help and exit |

Default paths are anchored to the script's location, so running it from another
directory does not change where it reads or writes. Explicit relative paths are
resolved from the current working directory. Neither output may overwrite the
source configuration.

## Output Formats

### JSON

The following is an illustrative snapshot using reserved documentation networks,
not real crawler IPs:

```json
{
  "schema_version": 1,
  "fetched_at": "2026-09-08T04:17:12.000000+00:00",
  "bots": {
    "example-bot": {
      "url": "https://example.com/bot.json",
      "creation_time": null,
      "prefixes": [
        "192.0.2.0/25",
        "192.0.2.128/25",
        "2001:db8::/32"
      ]
    }
  },
  "ipv4": ["192.0.2.0/24"],
  "ipv6": ["2001:db8::/32"]
}
```

| Field | Meaning |
| --- | --- |
| `schema_version` | Output schema version, currently `1` |
| `fetched_at` | UTC timestamp recorded after all feeds have been fetched and parsed |
| `bots` | Entries keyed by the IDs in the source configuration |
| `bots.<id>.url` | Configured feed URL |
| `bots.<id>.creation_time` | Provider's `creationTime`, copied as supplied, or `null` if absent |
| `bots.<id>.prefixes` | Validated, normalized, sorted CIDRs with exact duplicates removed within that bot |
| `ipv4`, `ipv6` | Sorted unions across all bots, with overlapping and mergeable adjacent networks collapsed |

Per-bot lists retain individual network boundaries; only the aggregate lists
collapse overlapping and adjacent networks. Collapsing does not add addresses
outside the original union. A network may appear under more than one bot.

`fetched_at` indicates when the data was retrieved, not when a provider last
changed it. Provider timestamps are not normalized or checked for freshness.

### Plain Text

The TXT file contains the JSON `ipv4` list followed by the `ipv6` list:

```text
192.0.2.0/24
2001:db8::/32
```

There are no bot labels, comments, or headers. Every range occupies one line,
including a trailing newline on the final line. Use the JSON file when you need
source attribution or freshness metadata.

## Custom Sources

Edit `sources.json` or supply another configuration with `--sources`:

```json
{
  "googlebot": "https://developers.google.com/search/apis/ipranges/googlebot.json",
  "bingbot": "https://www.bing.com/toolbox/bingbot.json"
}
```

The configuration must be a nonempty JSON object with nonempty bot IDs and HTTPS
URLs without embedded credentials. Each feed must return a nonempty `prefixes`
array in the following format:

```json
{
  "creationTime": "2026-09-08T00:00:00Z",
  "prefixes": [
    {"ipv4Prefix": "192.0.2.0/24"},
    {"ipv6Prefix": "2001:db8::/32"}
  ]
}
```

`creationTime` is optional. Every prefix entry must have at least one supported
IP field containing a valid CIDR of the matching address family. Networks with
host bits set, such as `192.0.2.1/24`, are rejected rather than silently widened.
Additional metadata fields are ignored.

Only this JSON feed format is supported. HTML pages, plain-text feeds, DNS-based
verification, and authenticated APIs do not have dedicated adapters.

## Automation

### GitHub Actions

[`Update bot IP lists`](.github/workflows/update-bot-ips.yml) runs on:

- A daily schedule at **04:17 UTC**.
- Manual dispatch through the repository's **Actions** tab.
- Pushes changing `bot_ips.py`, `sources.json`, `tests/**`, or the workflow itself.

The job uses Ubuntu and Python 3.12, runs the offline tests, fetches all feeds,
and commits and pushes both generated files to the branch used by the run
(the default branch for scheduled runs). No ZIP artifact is created.
The job has a 10-minute timeout and serializes execution per Git ref.

The latest published files are available directly in the repository:
[`data/bot-ips.json`](data/bot-ips.json) and
[`data/bot-ips.txt`](data/bot-ips.txt). Use GitHub's **Raw** button to download
either file without a ZIP, or pull the branch to retrieve both files locally.

> [!NOTE]
> To enable scheduled runs, place the project and workflow in a GitHub
> repository's default branch and enable Actions. GitHub schedules may be delayed;
> they are not a precise delivery-time guarantee.

The workflow requests `contents: write` and uses the built-in `GITHUB_TOKEN`;
no provider secrets are required. Repository policies and branch protection must
allow the workflow to push commits. Pushes are never forced: if the branch
advances during generation, the push fails safely and the workflow can be rerun.
If tests or generation fail, no commit is published. Unchanged files produce no
commit, but the JSON retrieval timestamp normally changes on each successful run.
Data-only commits do not match the workflow's push path filters.

### Local Scheduling

The CLI runs once and exits. It does not install a scheduler or run a background
service. For a Linux checkout at `/var/www/bot-ips`, a daily cron entry can use
`flock` to avoid overlapping local runs:

```cron
17 4 * * * flock -n /var/www/bot-ips/.update.lock /usr/bin/python3 /var/www/bot-ips/bot_ips.py
```

Adjust the paths for your installation. The cron user needs `flock`, Python,
network access, and write access to the project and output directories. Unlike
GitHub Actions, cron uses the scheduler's configured timezone. The CLI itself
does not lock concurrent runs.

## Reliability

- Fetches feeds with up to six concurrent workers and standard TLS certificate verification.
- Limits each response to 10 MiB.
- Makes up to three attempts for handled network failures, HTTP 429, and HTTP 5xx, waiting 1 and then 2 seconds between attempts.
- Does not retry other HTTP 4xx responses or invalid JSON/CIDR data.
- Refuses empty feeds and aborts generation if any configured source fails.
- Prepares both output files before replacing their destinations.

A download or validation failure leaves existing output files unchanged. Each
file is written to a temporary file in its destination directory, flushed,
synced, and atomically renamed. On POSIX systems, locally generated files use
owner-only permissions (`0600`); publishing them for another service requires
an explicit permissions or distribution step.

> [!WARNING]
> The two renames are **not one transaction**. A disk error or process interruption
> between them can leave JSON and TXT from different runs. Rerun generation if
> publication fails. A consumer requiring a consistent pair should consume only
> successfully completed snapshots, such as both files from the same CI commit.

| Exit Code | Meaning |
| --- | --- |
| `0` | Both files generated successfully, or help displayed |
| `1` | Handled configuration, download, validation, or filesystem error |
| `2` | Invalid command-line arguments |

Successful generation prints a summary to stdout; handled errors go to stderr.
Monitor both the exit status and the age of `fetched_at`. There is no built-in
staleness cutoff: a failed update intentionally leaves the last snapshot in place.

## Security Limits

An IP match is evidence that an address belongs to a published range, **not
authentication of a particular bot or proof that a request is safe**. Providers
can share infrastructure, and User-Agent strings can be spoofed.

The project does not perform forward-confirmed reverse DNS, enforce provider
verification guidance, or install firewall rules. Apply your own request
validation and freshness policy before using the output in access controls.
The combined list includes every configured bot; select per-bot JSON entries
when your policy should cover only a subset.

## Testing

Run the offline unit tests from the project directory:

```bash
python3 -m unittest discover -s tests -v
```

The suite covers CIDR validation and deduplication, aggregation and provenance,
JSON/TXT generation, preservation of previous data on fetch failure, temporary
file cleanup, output-path validation, and HTTP retry behavior. Network calls are
mocked; tests do not establish current provider availability.

For an end-to-end check without replacing the default snapshot:

```bash
python3 bot_ips.py --output /tmp/bot-ips-check.json
```

This fetches the live feeds and writes both `/tmp/bot-ips-check.json` and
`/tmp/bot-ips-check.txt`.

## Troubleshooting

| Symptom | What to Check |
| --- | --- |
| A provider returns HTTP 403 or 404 | Verify the configured URL and whether the provider restricts your network. These responses are not retried |
| Repeated timeouts, HTTP 429, or 5xx | Check connectivity and provider availability; consider a larger socket timeout or rerun later |
| Empty list or invalid prefix error | Inspect the named provider's feed for a format change. Do not bypass validation just to publish a new snapshot |
| Permission denied while writing | Check ownership and write permissions on the output directory |
| Another service cannot read local outputs | Files are created with mode `0600`; arrange an explicit publishing step |
| Missing or stale repository data | Check the workflow run status, Actions write permissions, and branch protection; rerun if a concurrent push rejected the update |

## Project Layout

```text
bot_ips.py                          CLI, fetching, validation, and output generation
sources.json                        Official feed configuration
tests/test_bot_ips.py               Offline unit tests
.github/workflows/update-bot-ips.yml Scheduled generation, commit, and push
data/bot-ips.json                   Generated structured snapshot (tracked in Git)
data/bot-ips.txt                    Generated merged CIDR list (tracked in Git)
```
