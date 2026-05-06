# CCF Bible Study Reminder Generator

This folder contains a script that generates a Chinese CCF reminder message and resolves the next week's `Note`, `Lecture`, `Questions`, and `Answers` links from Google Drive.

## File

- `ccf_preview_message.py`

## Supported workflow

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
