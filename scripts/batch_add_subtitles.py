#!/usr/bin/env python3
import os
import glob
import json
import requests
import subprocess
from pathlib import Path
from openai import OpenAI

# Transcription API configuration
API_URL = "<<url>>"
LANGUAGE = "zh"
TASK = "translate"

# vLLM configuration for translation
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_MODEL = os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "EMPTY")

def transcribe_video(mp4_file, json_file):
    """Transcribe video to JSON using API."""
    print(f"📥 Transcribing {mp4_file}...")

    try:
        with open(mp4_file, 'rb') as f:
            files = {'file': f}
            data = {
                'language': LANGUAGE,
                'task': TASK
            }

            response = requests.post(API_URL, files=files, data=data)
            response.raise_for_status()

            with open(json_file, 'wb') as out:
                out.write(response.content)

            print(f"✅ Saved transcript to {json_file}")
            return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Error transcribing {mp4_file}: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error transcribing {mp4_file}: {e}")
        return False

def translate_text(client, text, source_lang="Chinese", target_lang="Spanish"):
    """Translate text using vLLM service with OpenAI-compatible API."""
    system_prompt = f"""You are a professional translator specializing in video transcription translation.

Your task:
1. Translate from {source_lang} to {target_lang}
2. Preserve the natural spoken language style
3. Remove filler words, stutters, and false starts
4. Fix grammar while maintaining the original meaning
5. Keep technical terms accurate
6. Return ONLY the translated text, no explanations or notes

Focus on clarity and natural flow for video subtitles."""

    response = client.chat.completions.create(
        model=VLLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.3,
        max_tokens=2048
    )
    return response.choices[0].message.content.strip()

def translate_transcription(input_file, output_file):
    """Translate transcription JSON from Chinese to Spanish."""
    print(f"🌐 Translating {input_file}...")

    try:
        client = OpenAI(base_url=VLLM_BASE_URL, api_key=VLLM_API_KEY)

        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        num_segments = len(data.get('segments', []))
        data['language'] = 'es'

        for i, segment in enumerate(data['segments']):
            print(f"  Translating segment {i+1}/{num_segments}...")
            segment['text'] = translate_text(client, segment['text'])

            # Remove word-level data
            if 'words' in segment:
                del segment['words']

        # Remove word_segments from root
        if 'word_segments' in data:
            del data['word_segments']

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved translation to {output_file}")
        return True

    except Exception as e:
        print(f"❌ Error translating {input_file}: {e}")
        return False

def format_timestamp(seconds):
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def json_to_srt(json_file, srt_file):
    """Convert transcription JSON to SRT subtitle file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(srt_file, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(data['segments'], 1):
            f.write(f"{i}\n")
            start_time = format_timestamp(segment['start'])
            end_time = format_timestamp(segment['end'])
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{segment['text']}\n")
            f.write("\n")

def add_subtitles_to_video(video_file, srt_file, output_file):
    """Add subtitles to video using ffmpeg."""
    print(f"🎬 Adding subtitles to {video_file}...")

    cmd = [
        'ffmpeg',
        '-i', video_file,
        '-vf', f"subtitles={srt_file}:force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=2,MarginV=30'",
        '-c:v', 'libopenh264',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-y',
        output_file
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ Created subtitled video: {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error adding subtitles: {e}")
        return False
    except FileNotFoundError:
        print("❌ Error: ffmpeg not found. Please install ffmpeg.")
        return False

def main():
    # Find all MP4 files (exclude already subtitled ones)
    mp4_files = [f for f in glob.glob("*.mp4") if not f.endswith("_subtitled.mp4")]

    print(f"Found {len(mp4_files)} MP4 files to process")
    print("=" * 60)

    for mp4_file in mp4_files:
        print(f"\n📹 Processing: {mp4_file}")
        print("-" * 60)

        stem = Path(mp4_file).stem
        json_file = f"{stem}.json"
        json_es_file = f"{stem}-es.json"
        srt_file = f"{stem}-es.srt"
        output_video = f"{stem}_subtitled.mp4"

        # Step 1: Transcribe
        if os.path.exists(json_file):
            print(f"⏭️  Transcription exists: {json_file}")
        else:
            if not transcribe_video(mp4_file, json_file):
                print(f"⚠️  Skipping {mp4_file} due to transcription error")
                continue

        # Step 2: Translate
        if os.path.exists(json_es_file):
            print(f"⏭️  Translation exists: {json_es_file}")
        else:
            if not translate_transcription(json_file, json_es_file):
                print(f"⚠️  Skipping {mp4_file} due to translation error")
                continue

        # Step 3: Add subtitles
        if os.path.exists(output_video):
            print(f"⏭️  Subtitled video exists: {output_video}")
        else:
            # Create SRT file
            json_to_srt(json_es_file, srt_file)

            if not add_subtitles_to_video(mp4_file, srt_file, output_video):
                print(f"⚠️  Failed to add subtitles to {mp4_file}")
                continue

        print(f"✨ Completed: {mp4_file} → {output_video}")

    print("\n" + "=" * 60)
    print("🎉 Batch processing complete!")

if __name__ == "__main__":
    main()

