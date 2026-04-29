from http.server import BaseHTTPRequestHandler
import json
import re


def optimize_transcript(content: str) -> str:
    """
    Convert high-token transcript formats (VTT/TXT) into Token-Optimized Inline Format.
    """
    lines = content.split('\n')
    optimized_lines = []
    cleaned_lines = []
    skip_next = False

    for line in lines:
        line_stripped = line.strip()

        if not line_stripped:
            continue

        if line_stripped.startswith('WEBVTT'):
            continue

        if line_stripped.startswith('NOTE') or line_stripped.startswith('STYLE'):
            skip_next = True
            continue

        if line_stripped.isdigit():
            continue

        if skip_next:
            if not line_stripped:
                skip_next = False
            continue

        cleaned_lines.append(line_stripped)

    # Regex patterns for different timestamp formats
    vtt_pattern = re.compile(
        r'^(\d{1,2}):(\d{2}):(\d{2})(?:[.,]\d+)?\s*-->\s*\d{1,2}:\d{2}:\d{2}(?:[.,]\d+)?$'
    )
    bracket_pattern = re.compile(
        r'^\[(\d{1,2}):(\d{2}):(\d{2})(?:[.,]\d+)?\](.*)$|^\[(\d{1,2}):(\d{2})(?:[.,]\d+)?\](.*)$'
    )
    standalone_pattern = re.compile(
        r'^(\d{1,2}):(\d{2}):(\d{2})(?:[.,]\d+)?(?:\s+(.*))?$'
    )

    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]

        vtt_match = vtt_pattern.match(line)
        if vtt_match:
            h, m, s = vtt_match.groups()
            timestamp = format_timestamp(h, m, s)

            text_parts = []
            i += 1
            while i < len(cleaned_lines):
                next_line = cleaned_lines[i]
                if vtt_pattern.match(next_line) or bracket_pattern.match(next_line) or standalone_pattern.match(next_line):
                    break
                text_parts.append(next_line)
                i += 1

            text = ' '.join(text_parts).strip()
            if text:
                optimized_lines.append(f"[{timestamp}] {text}")
            continue

        bracket_match = bracket_pattern.match(line)
        if bracket_match:
            groups = bracket_match.groups()
            if groups[0] is not None:
                h, m, s = groups[0], groups[1], groups[2]
                inline_text = groups[3] or ''
            else:
                h = '0'
                m, s = groups[4], groups[5]
                inline_text = groups[6] or ''

            timestamp = format_timestamp(h, m, s)

            text_parts = [inline_text.strip()] if inline_text.strip() else []
            i += 1
            while i < len(cleaned_lines):
                next_line = cleaned_lines[i]
                if vtt_pattern.match(next_line) or bracket_pattern.match(next_line) or standalone_pattern.match(next_line):
                    break
                text_parts.append(next_line)
                i += 1

            text = ' '.join(text_parts).strip()
            if text:
                optimized_lines.append(f"[{timestamp}] {text}")
            continue

        standalone_match = standalone_pattern.match(line)
        if standalone_match:
            h, m, s, inline_text = standalone_match.groups()
            timestamp = format_timestamp(h, m, s)

            text_parts = [inline_text.strip()] if inline_text and inline_text.strip() else []
            i += 1
            while i < len(cleaned_lines):
                next_line = cleaned_lines[i]
                if vtt_pattern.match(next_line) or bracket_pattern.match(next_line) or standalone_pattern.match(next_line):
                    break
                text_parts.append(next_line)
                i += 1

            text = ' '.join(text_parts).strip()
            if text:
                optimized_lines.append(f"[{timestamp}] {text}")
            continue

        i += 1

    return '\n'.join(optimized_lines)


def format_timestamp(h: str, m: str, s: str) -> str:
    hour = int(h)
    minute = int(m)
    second = s.zfill(2)

    if hour == 0:
        return f"{minute}:{second}"
    else:
        return f"{hour}:{str(minute).zfill(2)}:{second}"


def calculate_savings(original: str, optimized: str) -> dict:
    original_tokens = len(original) // 4
    optimized_tokens = len(optimized) // 4

    if original_tokens > 0:
        percent_saved = ((original_tokens - optimized_tokens) / original_tokens) * 100
    else:
        percent_saved = 0

    return {
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "tokens_saved": original_tokens - optimized_tokens,
        "percent_saved": round(percent_saved, 1)
    }


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            data = json.loads(body)
            content = data.get('content', '')

            if not content:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No content provided"}).encode())
                return

            optimized = optimize_transcript(content)
            savings = calculate_savings(content, optimized)

            response = {
                "optimized": optimized,
                "stats": savings
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
