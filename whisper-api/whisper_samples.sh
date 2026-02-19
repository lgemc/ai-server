#!/bin/bash

# Whisper API sample commands
# Usage: ./whisper_samples.sh <command> [options]

API_URL="${WHISPER_API_URL:-http://localhost:8001}"

case "$1" in
  sync)
    # Synchronous transcription (blocks until done)
    # Usage: ./whisper_samples.sh sync /path/to/video.mp4 [language] [task]
    FILE="${2:?Usage: $0 sync <file> [language] [task]}"
    LANG="${3:-en}"
    TASK="${4:-transcribe}"
    curl -X POST "$API_URL/transcribe" \
      -F "file=@$FILE" \
      -F "language=$LANG" \
      -F "task=$TASK"
    ;;

  async)
    # Submit async job and return job_id
    # Usage: ./whisper_samples.sh async /path/to/video.mp4 [language] [task]
    FILE="${2:?Usage: $0 async <file> [language] [task]}"
    LANG="${3:-en}"
    TASK="${4:-transcribe}"
    curl -s -X POST "$API_URL/transcribe/async" \
      -F "file=@$FILE" \
      -F "language=$LANG" \
      -F "task=$TASK" | jq .
    ;;

  status)
    # Check job status
    # Usage: ./whisper_samples.sh status <job_id>
    JOB_ID="${2:?Usage: $0 status <job_id>}"
    curl -s "$API_URL/transcribe/status/$JOB_ID" | jq .
    ;;

  poll)
    # Submit and poll until complete
    # Usage: ./whisper_samples.sh poll /path/to/video.mp4 [language] [task]
    FILE="${2:?Usage: $0 poll <file> [language] [task]}"
    LANG="${3:-en}"
    TASK="${4:-transcribe}"

    echo "Submitting job..."
    JOB_ID=$(curl -s -X POST "$API_URL/transcribe/async" \
      -F "file=@$FILE" \
      -F "language=$LANG" \
      -F "task=$TASK" | jq -r '.job_id')

    echo "Job ID: $JOB_ID"
    echo "Polling for progress..."

    while true; do
      RESP=$(curl -s "$API_URL/transcribe/status/$JOB_ID")
      STATUS=$(echo "$RESP" | jq -r '.status')
      PROGRESS=$(echo "$RESP" | jq -r '.progress')
      echo "Status: $STATUS | Progress: $PROGRESS%"

      if [[ "$STATUS" == "completed" ]]; then
        echo ""
        echo "=== TRANSCRIPT ==="
        echo "$RESP" | jq -r '.result.text'
        break
      elif [[ "$STATUS" == "failed" ]]; then
        echo "Error: $(echo "$RESP" | jq -r '.error')"
        exit 1
      fi
      sleep 2
    done
    ;;

  jobs)
    # List all jobs
    curl -s "$API_URL/transcribe/jobs" | jq .
    ;;

  delete)
    # Delete a job
    # Usage: ./whisper_samples.sh delete <job_id>
    JOB_ID="${2:?Usage: $0 delete <job_id>}"
    curl -s -X DELETE "$API_URL/transcribe/jobs/$JOB_ID" | jq .
    ;;

  health)
    # Health check
    curl -s "$API_URL/health" | jq .
    ;;

  *)
    echo "Whisper API CLI"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  sync   <file> [lang] [task]   Synchronous transcription (blocks)"
    echo "  async  <file> [lang] [task]   Submit async job, returns job_id"
    echo "  poll   <file> [lang] [task]   Submit and poll until complete"
    echo "  status <job_id>               Check job status"
    echo "  jobs                          List all jobs"
    echo "  delete <job_id>               Delete a completed job"
    echo "  health                        API health check"
    echo ""
    echo "Options:"
    echo "  lang: en, es, fr, etc. (default: en)"
    echo "  task: transcribe | translate (default: transcribe)"
    echo ""
    echo "Examples:"
    echo "  $0 poll video.mp4"
    echo "  $0 sync audio.mp3 es"
    echo "  $0 async video.mp4 es translate"
    ;;
esac
