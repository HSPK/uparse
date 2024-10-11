from ..schema.page import Page


def remove_watermarks(pages: list[Page], freq_thresh: int | float = 0.4, least_span: int = 10):
    # remove watermarks span, occuring more than freq_thresh
    all_watermarks = []
    for page in pages:
        span_text_freq = {}
        span_count = 0
        for block in page.blocks:
            for line in block.lines:
                for span in line.spans:
                    span_text_freq[span.text.strip()] = span_text_freq.get(span.text.strip(), 0) + 1
                    span_count += 1
        if span_count < least_span:
            # skip pages with too few spans
            continue
        span_text_freq_sorted = sorted(span_text_freq.items(), key=lambda x: x[1], reverse=True)
        thresh = freq_thresh if isinstance(freq_thresh, int) else freq_thresh * len(span_text_freq)
        watermarks = [text for text, freq in span_text_freq_sorted if freq > thresh]
        all_watermarks.extend(watermarks)
        new_blocks = []
        for block in page.blocks:
            new_lines = []
            for line in block.lines:
                new_spans = []
                for span in line.spans:
                    if span.text.strip() not in watermarks:
                        new_spans.append(span)
                if new_spans:
                    line.spans = new_spans
                    new_lines.append(line)
            if new_lines:
                block.lines = new_lines
                new_blocks.append(block)
        page.blocks = new_blocks
    return all_watermarks
