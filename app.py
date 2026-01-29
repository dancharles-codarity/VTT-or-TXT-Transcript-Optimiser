import streamlit as st
import re

st.set_page_config(
    page_title="SOP Token Optimizer",
    page_icon="📝",
    layout="centered"
)


def optimize_transcript(content: str) -> str:
    """
    Convert high-token transcript formats (VTT/TXT) into Token-Optimized Inline Format.

    Handles:
    - VTT format: 00:04:12.539 --> 00:04:15.000
    - TXT format with brackets: [00:04:12.539]
    - TXT format without brackets: 00:04:12.539
    - Various timestamp precisions (with or without milliseconds)
    """
    lines = content.split('\n')
    optimized_lines = []

    # Remove VTT header, metadata, and common artifacts
    # Strip WEBVTT header, NOTE blocks, STYLE blocks, and sequence numbers
    cleaned_lines = []
    skip_next = False

    for line in lines:
        line_stripped = line.strip()

        # Skip empty lines
        if not line_stripped:
            continue

        # Skip WEBVTT header
        if line_stripped.startswith('WEBVTT'):
            continue

        # Skip NOTE and STYLE blocks
        if line_stripped.startswith('NOTE') or line_stripped.startswith('STYLE'):
            skip_next = True
            continue

        # Skip lines that are just sequence numbers (digits only)
        if line_stripped.isdigit():
            continue

        # Skip continuation of NOTE/STYLE blocks (until empty line)
        if skip_next:
            if not line_stripped:
                skip_next = False
            continue

        cleaned_lines.append(line_stripped)

    # Regex patterns for different timestamp formats
    # VTT format: 00:04:12.539 --> 00:04:15.000 or 00:04:12,539 --> 00:04:15,000
    vtt_pattern = re.compile(
        r'^(\d{1,2}):(\d{2}):(\d{2})(?:[.,]\d+)?\s*-->\s*\d{1,2}:\d{2}:\d{2}(?:[.,]\d+)?$'
    )

    # Bracketed timestamp: [00:04:12.539] or [00:04:12] or [4:12]
    bracket_pattern = re.compile(
        r'^\[(\d{1,2}):(\d{2}):(\d{2})(?:[.,]\d+)?\](.*)$|^\[(\d{1,2}):(\d{2})(?:[.,]\d+)?\](.*)$'
    )

    # Standalone timestamp at start of line: 00:04:12.539 or 0:04:12
    standalone_pattern = re.compile(
        r'^(\d{1,2}):(\d{2}):(\d{2})(?:[.,]\d+)?(?:\s+(.*))?$'
    )

    # Process lines
    i = 0
    while i < len(cleaned_lines):
        line = cleaned_lines[i]

        # Check for VTT timestamp line (timestamp --> timestamp)
        vtt_match = vtt_pattern.match(line)
        if vtt_match:
            h, m, s = vtt_match.groups()
            timestamp = format_timestamp(h, m, s)

            # Collect all text until next timestamp or end
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

        # Check for bracketed timestamp with possible inline text
        bracket_match = bracket_pattern.match(line)
        if bracket_match:
            groups = bracket_match.groups()
            # Full format [HH:MM:SS]
            if groups[0] is not None:
                h, m, s = groups[0], groups[1], groups[2]
                inline_text = groups[3] or ''
            # Short format [MM:SS]
            else:
                h = '0'
                m, s = groups[4], groups[5]
                inline_text = groups[6] or ''

            timestamp = format_timestamp(h, m, s)

            # Collect text (inline + following lines until next timestamp)
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

        # Check for standalone timestamp
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

        # If no timestamp pattern matched, skip this line (likely orphaned text)
        i += 1

    return '\n'.join(optimized_lines)


def format_timestamp(h: str, m: str, s: str) -> str:
    """
    Format timestamp to minimal form:
    - If hour is 00: return M:SS (e.g., 4:12)
    - If hour is non-zero: return H:MM:SS (e.g., 1:05:22)
    """
    hour = int(h)
    minute = int(m)
    second = s.zfill(2)  # Ensure seconds are zero-padded

    if hour == 0:
        return f"{minute}:{second}"
    else:
        return f"{hour}:{str(minute).zfill(2)}:{second}"


def calculate_token_savings(original: str, optimized: str) -> tuple[int, int, float]:
    """
    Estimate token savings (rough approximation: ~4 chars per token).
    Returns (original_tokens, optimized_tokens, percent_saved).
    """
    # Rough token estimation (GPT models average ~4 chars per token)
    original_tokens = len(original) // 4
    optimized_tokens = len(optimized) // 4

    if original_tokens > 0:
        percent_saved = ((original_tokens - optimized_tokens) / original_tokens) * 100
    else:
        percent_saved = 0

    return original_tokens, optimized_tokens, percent_saved


# Main UI
st.title("📝 SOP Token Optimizer")
st.markdown("""
Upload your **VTT** or **TXT** transcript to reduce token usage by **~50%**
while keeping timing data for creating SOPs and video chapters with LLMs.
""")

st.divider()

# File uploader
uploaded_file = st.file_uploader(
    "Drag & drop your transcript file",
    type=['vtt', 'txt'],
    help="Supports WebVTT (.vtt) and text (.txt) transcript formats"
)

if uploaded_file:
    # Read and decode file
    raw_text = uploaded_file.getvalue().decode("utf-8")

    # Optimize the transcript
    optimized_text = optimize_transcript(raw_text)

    # Calculate savings
    orig_tokens, opt_tokens, savings = calculate_token_savings(raw_text, optimized_text)

    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Original (est. tokens)", f"{orig_tokens:,}")
    with col2:
        st.metric("Optimized (est. tokens)", f"{opt_tokens:,}")
    with col3:
        st.metric("Tokens Saved", f"{savings:.1f}%", delta=f"-{orig_tokens - opt_tokens:,}")

    st.divider()

    # Preview section
    st.subheader("📋 Optimized Output")

    # Show preview (first 10 lines)
    preview_lines = optimized_text.split('\n')[:10]
    preview_text = '\n'.join(preview_lines)
    if len(optimized_text.split('\n')) > 10:
        preview_text += '\n... (showing first 10 lines)'

    st.text_area(
        "Preview (first 10 lines):",
        preview_text,
        height=250,
        disabled=True
    )

    # Full output for copying
    st.text_area(
        "Full optimized transcript (select all & copy):",
        optimized_text,
        height=300,
        key="full_output"
    )

    # Download button
    original_name = uploaded_file.name.rsplit('.', 1)[0]
    st.download_button(
        label="⬇️ Download Optimized TXT",
        data=optimized_text,
        file_name=f"optimized_{original_name}.txt",
        mime="text/plain",
        use_container_width=True
    )

else:
    # Show example when no file uploaded
    st.info("👆 Upload a transcript file to get started")

    with st.expander("📖 Example: Before & After"):
        st.markdown("**Before (VTT format - high tokens):**")
        st.code("""WEBVTT

1
00:00:11.539 --> 00:00:14.000
Welcome to today's tutorial on
setting up your dashboard.

2
00:00:14.500 --> 00:00:18.000
First, navigate to the settings panel
by clicking the gear icon.""", language=None)

        st.markdown("**After (Optimized - ~50% fewer tokens):**")
        st.code("""[0:11] Welcome to today's tutorial on setting up your dashboard.
[0:14] First, navigate to the settings panel by clicking the gear icon.""", language=None)

# Footer
st.divider()
st.caption("Built for creating SOPs and video chapters with LLMs. Timestamps are simplified to [M:SS] or [H:MM:SS] format.")
