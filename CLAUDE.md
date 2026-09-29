# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is Chris Callison-Burch's academic website, built with Jekyll and hosted on GitHub Pages. The site showcases publications, lab members, teaching, and media presence.

## Build Commands

```bash
# Install dependencies (one-time setup)
gem install jekyll
gem install github-pages

# Build and serve locally
jekyll build --watch &
jekyll serve
# Visit http://localhost:4000/
```

## Architecture

### Data-Driven Content

All dynamic content lives in YAML files under `_data/`. Pages use Liquid templates to iterate over this data rather than hardcoding content.

Key data files:
- `publications.yaml` - 300+ publications with metadata (title, authors, venue, year, URLs, bibtex, abstracts, press coverage)
- `students.yaml` / `students_graduated.yaml` - Current and past lab members
- `teaching.yaml` - Course history with enrollment and ratings
- `grants.yaml` - Research funding
- `talks.yaml` - Speaking engagements
- `press.yaml` - Media mentions
- `employment.yaml` / `education.yaml` - CV information

### Page Structure

- Markdown pages (`*.md` in root) define page content and front matter
- `_layouts/default.html` provides the main template with Bootstrap 3 styling
- Pages pull data using Liquid syntax: `{% for item in site.data.filename %}`

### Assets

- `assets/img/students/` - Student photos
- `publications/` - PDF storage for papers and dissertations
- `dist/` - Bootstrap CSS/JS distribution files

## Common Tasks

**Adding a publication:** Add entry to `_data/publications.yaml` with fields: title, authors, venue, year, url, abstract, bibtex

**Adding a student:** Add entry to `_data/students.yaml` with: name, degree, school, photo, homepage, expected_graduation. Move to `students_graduated.yaml` when they graduate.

**Updating office hours/contact info:** Edit the `caption` field in `index.md` front matter

**Adding press coverage:** Add to `_data/press.yaml` or link within a publication entry in `publications.yaml`

## Technology Stack

- Jekyll 4.3.3 with Kramdown markdown processor
- Bootstrap 3 for styling
- MathJax for equations
- Font Awesome 4.0.3 for icons
- Custom Pandoc plugin available in `_plugins/pandoc_markdown.rb`
