# Copyleft Cultivars Website

Source for the Copyleft Cultivars website: a [Quarto](https://quarto.org) website
built to static HTML and published to GitHub Pages.

## Local development

### 1. Install Quarto

Quarto is the only requirement. The site is plain Markdown — there are no
executable code cells — so you do **not** need Python, R, or Jupyter installed.

**Linux (user-local, no sudo required):**

```bash
QUARTO_VERSION=1.10.18
curl -sSL -o /tmp/quarto.tar.gz \
  "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.tar.gz"
mkdir -p ~/.local/share ~/.local/bin
tar -xzf /tmp/quarto.tar.gz -C ~/.local/share
ln -sfn ~/.local/share/quarto-${QUARTO_VERSION}/bin/quarto ~/.local/bin/quarto
```

Make sure `~/.local/bin` is on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"   # add to ~/.profile or ~/.bashrc to persist
```

**macOS:** `brew install --cask quarto`

**Windows:** download and run the `.msi` installer.

Prebuilt installers for every platform are listed at
<https://quarto.org/docs/get-started/>.

Verify the install:

```bash
quarto --version
```

### 2. Preview and render

```bash
quarto preview    # live-reloading server, usually http://localhost:4200
quarto render     # one-off build into _site/
```

Leave `quarto preview` running while you edit — it rebuilds the affected pages
on save and reloads the browser automatically. Use `quarto render` when you just
want the finished HTML in `_site/`.

If port 4200 is taken: `quarto preview --port 4444`.

## Project structure

| Path | Purpose |
| --- | --- |
| `*.qmd` | One file per page — `index`, `about`, `preservation`, `initiatives`, `events`, `news`, `faq`, `support` |
| `news/*.qmd` | News posts. Listed manually in `news.qmd`, newest first. |
| `_quarto.yml` | Site config: navbar, footer, page list, HTML format options |
| `_brand.yml` | Brand colors and fonts (used by the `brand` theme) |
| `styles.css` | Custom CSS: events timeline, news listing, theme tweaks |
| `images/` | Site images |
| `_site/` | Build output — generated, never committed |

## Content conventions

- **Adding or renaming a page** means updating the `website.navbar` list in
  `_quarto.yml`, or it won't appear in the menu.
- **Adding an upcoming event:** `events.qmd` has a commented-out
  `<div class="event-card">…</div>` template under "Upcoming Events". Copy it,
  paste it above the comment, and edit the text.
- **Adding a past event:** add two matching pieces in `events.qmd` — an
  `<article class="event-detail" id="ev-my-event">…</article>` panel, and an
  `<li>` in the timeline rail. The rail button's `data-event` must equal the
  panel's `id`, or clicking it won't do anything.
- **Publishing a news post:** rename it out of draft
  (`news/_my-post.qmd` → `news/my-post.qmd`), then add an entry to `news.qmd`
  in the format shown in the comment at the bottom of that file.
- **Unpublished drafts:** prefix the filename with an underscore
  (`news/_my-post.qmd`). Quarto ignores underscore-prefixed files completely, so
  a draft never builds, never ships, and never appears in the news list.
- **`_private/`** holds local reference material (gitignored, and skipped by
  Quarto because of the leading underscore). Nothing in it ships with the site.
- **Raw HTML blocks:** Quarto switches a page to its own full-width grid as soon
  as the document contains top-level raw HTML, which can fight custom CSS. That
  is already neutralized for the events archive in `styles.css`; on new pages,
  prefer fenced divs (`::: {.my-class}`) over raw `<div>` blocks.
- **Colors and fonts** live in `_brand.yml`, not in the theme CSS — Quarto
  recompiles the theme from there on every render.
- `_site/`, `.quarto/`, and `_freeze/` are gitignored; never commit them.

## Publishing

Deployment is automated. Pushing to `main` runs
`.github/workflows/publish.yml`, which renders the site in CI and publishes it
to the `gh-pages` branch. Nothing needs to be pushed from your machine beyond
the source files.

## License

Copyright © 2025 Copyleft Cultivars. Except where otherwise noted, content is
licensed under
[CC-BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
