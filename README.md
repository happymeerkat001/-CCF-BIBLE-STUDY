# CCF Bible Study Tools

This folder contains scripts for CCF Bible study preparation.

## Files

- `ccf_preview_message.py`
- `ccf_diagram.py`
- `index_bdag.py`
- `index_commentary_pdf.py`

## Reminder message workflow

Use a Bible reference plus last week's lesson code:

```bash
python3 ccf_preview_message.py --reference "John 12:20-50" --previous-lesson L15
```

Chinese short form also works:

```bash
python3 ccf_preview_message.py --reference "约12:20-50" --previous-lesson L15
```

## Accepted reference formats

- `John 12:20-50`
- `Jn 12:20-50`
- `约翰福音12:20-50`
- `约12:20-50`

## Example output

```text
这周我们会查考约翰福音13:1-30节的内容，预查时间是周四（5/7）晚上7:30-8:30（CT），请预留时间，谢谢！

以下是CCF 资料：

Note
https://drive.google.com/file/d/1e9qQ_Iv6X_7557rwy2iluzLFLb-cZzZ8/view?usp=drivesdk

Lecture
https://drive.google.com/file/d/1EvbgjiYbMggaO5WDTQJDVa3xn27k1Dy8/view?usp=drivesdk

Questions
https://drive.google.com/file/d/1LQTY_Zoely9ag2PeURHnkD7L3ofcGHJP/view?usp=drivesdk

Answers
https://drive.google.com/file/d/1U7oFokmS718vEDkpuRj2CSldPubwljWv/view?usp=drivesdk

The google drive for these resources are:
https://drive.google.com/drive/mobile/folders/1g_1yAlDiOFy46OKpEJFbECHdbXDDdLME?usp=sharing
```

## Optional flags

```bash
python3 ccf_preview_message.py \
  --reference "约12:20-50" \
  --previous-lesson L15 \
  --mentions @Amber @mouxiaoyu @Zhicun \
  --date 2026-05-07 \
  --weekday 周四 \
  --time 晚上8:00-9:00 \
  --tz CT
```

## Notes

- `--previous-lesson` is required.
- The script assumes this week's files are the next lesson, for example `L15 -> L16`.
- The script requires internet access because it reads the public Google Drive pages at runtime.

## Diagram workflow

`ccf_diagram.py` builds an English sentence-diagram draft by combining:

- MACULA Greek syntax trees cached under `data/`
- API.Bible verse text
- OpenRouter for English clause mapping and HTML formatting

### Environment

Store secrets in `.env`:

```bash
OPENROUTER_API_KEY=...
BIBLE_API_KEY=...
# Preferred NASB ID:
BIBLE_ID=a761ca71e0b3ddcf-01
# Optional Obsidian publish destination. Defaults to:
# /Users/leon/Library/Mobile Documents/iCloud~md~obsidian/Documents/Neural-orchestrator/Bible Study
OBSIDIAN_BIBLE_STUDY_DIR="~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Neural-orchestrator/Bible Study"
```

### Usage

```bash
python3 ccf_diagram.py "John 6"
python3 ccf_diagram.py "John 6:1-21"
python3 ccf_diagram.py "John 6" --model "deepseek/deepseek-chat-v3-0324"
python3 ccf_diagram.py "John 6:1-14" --dump-prompt
python3 ccf_diagram.py "John 6:1-14" --english-source macula-gloss
python3 ccf_diagram.py "John 12:20-50" --footnotes
python3 ccf_diagram.py "John 12:20-50" --footnotes --footnotes-style inline
python3 ccf_diagram.py "John 6:1-14" --publish-dir "/tmp/Bible Study"
python3 ccf_diagram.py "John 6:1-14" --publish-mode move
python3 ccf_diagram.py "John 6:1-14" --no-publish
```

Outputs are always written to `output/` first, then published to the Obsidian vault copy by default at `/Users/leon/Library/Mobile Documents/iCloud~md~obsidian/Documents/Neural-orchestrator/Bible Study`.

### Main command: diagram + commentary + word study

If you want the full output for a passage, including:

- the sentence diagram
- foldable commentary blocks
- bolded Greek-linked word-study terms

run:

```bash
  python3 ccf_diagram.py "John 13:1-30" \
    --footnotes \
    --commentary-sources fbc,net \
    --bold-words
```

If you only want the built-in web sources for now:

```bash
python3 ccf_diagram.py "John 6:1-5" \
  --footnotes \
  --commentary-sources fbc,net \
  --bold-words
```

If you want every configured source:

```bash
python3 ccf_diagram.py "John 6:1-5" \
  --footnotes \
  --commentary-sources all \
  --bold-words
```

`--footnotes` is the master switch for commentary output. `--bold-words` is independent and requires a local BDAG index.

### One-time indexing commands

Before using `--bold-words`, build the BDAG index once:

```bash
python3 index_bdag.py --url "https://example.com/path/to/bdag.pdf"
```

You can also provide the URL through `BDAG_PDF_URL`:

```bash
BDAG_PDF_URL="https://example.com/path/to/bdag.pdf" python3 index_bdag.py
```

This writes:

- `data/bdag.pdf`
- `data/bdag_index.json`

Before using local PDF commentary sources such as `keener`, build each book index once:

```bash
python3 index_commentary_pdf.py --pdf "/real/path/to/keener.pdf" --book john --key keener
```

This writes files such as:

- `data/keener_john.json`

Use a real PDF path. `path/to/...` in examples is a placeholder, so the command will fail until the PDF exists at that location. Run scripts with `python3 script_name.py` from this folder, or `./script_name.py` only after making the script executable and using the `./` prefix.

### Notes

- The first run downloads the MACULA XML file for the requested book and caches it under `data/`.
- The script uses `BIBLE_ID` first, so you can pin NASB directly instead of relying on discovery.
- If API.Bible is unavailable or your key is not authorized, `--english-source macula-gloss` uses MACULA glosses as the English source.
- `--dump-prompt` is useful for prompt tuning before spending tokens.
- `--footnotes` appends commentary after each verse block.
- `--commentary-sources` accepts `fbc`, `net`, `keener`, or `all`.
- `--footnotes-style collapse` is the default and renders nested `<details>` blocks: one outer block per verse, then one inner block per commentary source.
- `--footnotes` with no `--commentary-sources` uses `fbc` by default for backward compatibility.
- `--bold-words` bolds lexically significant Greek-linked English terms inside the generated diagram and requires `data/bdag_index.json`.
- The `net` source currently depends on what `labs.bible.org` exposes for the requested passage; if only note markers are available, the output may fall back to marker-context snippets instead of full note bodies.
- `--publish-dir` overrides the vault destination for one run, `--publish-mode move` removes the local file after a successful publish, and `--no-publish` disables vault publishing entirely.
- If the Obsidian/iCloud destination is unavailable, the script prints a warning to stderr and still keeps the local output as a successful run.
