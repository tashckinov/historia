from historia_bot.formatting import format_advisor_message


def test_format_advisor_message_converts_escaped_newlines_and_bold():
    raw = r"1. **Укрепление союзов**\n2. **Энергетика**"
    formatted = format_advisor_message(raw)
    assert "\n" in formatted
    assert "<b>Укрепление союзов</b>" in formatted
    assert "<b>Энергетика</b>" in formatted


def test_format_advisor_message_escapes_html():
    raw = r"<script>bad</script>"
    formatted = format_advisor_message(raw)
    assert "&lt;script&gt;bad&lt;/script&gt;" in formatted
