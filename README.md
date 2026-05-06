# CCF Bible Study Tools

This folder contains scripts for CCF Bible study preparation.

## Files

- `ccf_preview_message.py`
- `ccf_diagram.py`

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
python3 ccf_diagram.py --reference "John 6"
python3 ccf_diagram.py --reference "John 6:1-21"
python3 ccf_diagram.py --reference "John 6" --model "deepseek/deepseek-chat-v3-0324"
python3 ccf_diagram.py --reference "John 6:1-14" --dump-prompt
python3 ccf_diagram.py --reference "John 6:1-14" --english-source macula-gloss
python3 ccf_diagram.py --reference "John 12:20-50" --footnotes
python3 ccf_diagram.py --reference "John 12:20-50" --footnotes --footnotes-style inline
python3 ccf_diagram.py --reference "John 6:1-14" --publish-dir "/tmp/Bible Study"
python3 ccf_diagram.py --reference "John 6:1-14" --publish-mode move
python3 ccf_diagram.py --reference "John 6:1-14" --no-publish
```

Outputs are always written to `output/` first, then published to the Obsidian vault copy by default at `/Users/leon/Library/Mobile Documents/iCloud~md~obsidian/Documents/Neural-orchestrator/Bible Study`.

### Notes

- The first run downloads the MACULA XML file for the requested book and caches it under `data/`.
- The script uses `BIBLE_ID` first, so you can pin NASB directly instead of relying on discovery.
- If API.Bible is unavailable or your key is not authorized, `--english-source macula-gloss` uses MACULA glosses as the English source.
- `--dump-prompt` is useful for prompt tuning before spending tokens.
- `--footnotes` appends Dr. Bob Utley's FreeBibleCommentary notes per verse; `--footnotes-style collapse` (default) uses `<details>` blocks for Obsidian-friendly folding.
- `--publish-dir` overrides the vault destination for one run, `--publish-mode move` removes the local file after a successful publish, and `--no-publish` disables vault publishing entirely.
- If the Obsidian/iCloud destination is unavailable, the script prints a warning to stderr and still keeps the local output as a successful run.
