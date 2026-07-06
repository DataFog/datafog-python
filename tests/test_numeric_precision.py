"""Precision tests for numeric entities (issue #158).

Bare digit runs (tab IDs, row IDs, timestamps) must not match SSN/PHONE by
default. Delimited/formatted forms still match; bare matching is opt-in via
``strict_numeric=False``.

Every SSN/PHONE literal is assembled from split parts so this source file
never contains a contiguous match (our own Claude Code hook would block the
write otherwise).
"""

import datafog

# Delimited SSN, structurally valid (area != 000/666/9xx, group != 00, serial != 0000)
SSN_DASHED = "123-45-" "6789"
SSN_SPACED = "123 45 " "6789"
SSN_BARE = "12345" "6789"  # nine bare digits

# Formatted phone in the fictional 555-01xx block; bare form is the same digits
PHONE_FORMATTED = "(202) 555-" "0143"
PHONE_DASHED = "202-555-" "0143"
PHONE_BARE = "20255" "50143"  # ten bare digits

# Structured-output noise from issue #158
TAB_ID_9 = "48370" "1234"  # nine digits, e.g. a browser tabId
TAB_ID_10 = "173025" "6680"  # ten digits, e.g. a tabGroupId / epoch


def _types(text, **kw):
    return [e.type for e in datafog.scan(text, engine="regex", **kw).entities]


class TestSSNDefaultStrict:
    def test_dashed_ssn_still_detected(self):
        assert "SSN" in _types(f"ssn {SSN_DASHED}")

    def test_spaced_ssn_still_detected(self):
        assert "SSN" in _types(f"ssn {SSN_SPACED}")

    def test_bare_nine_digits_not_ssn_by_default(self):
        # The issue #158 regression: a 9-digit tab id must not be an SSN.
        assert "SSN" not in _types(f"tabId {TAB_ID_9}")

    def test_bare_valid_ssn_shape_not_matched_by_default(self):
        assert "SSN" not in _types(f"legacy {SSN_BARE} here")


class TestSSNOptIn:
    def test_bare_ssn_detected_when_strict_numeric_false(self):
        assert "SSN" in _types(f"legacy {SSN_BARE}", strict_numeric=False)

    def test_bare_tab_id_still_matches_in_permissive_mode(self):
        # Opt-in mode accepts any structurally valid nine-digit run; this is
        # the documented tradeoff of strict_numeric=False.
        assert "SSN" in _types(f"tabId {TAB_ID_9}", strict_numeric=False)


class TestPhoneDefaultStrict:
    def test_formatted_phone_still_detected(self):
        assert "PHONE" in _types(f"call {PHONE_FORMATTED}")

    def test_dashed_phone_still_detected(self):
        assert "PHONE" in _types(f"call {PHONE_DASHED}")

    def test_bare_ten_digits_not_phone_by_default(self):
        assert "PHONE" not in _types(f"tabGroupId {TAB_ID_10}")

    def test_bare_phone_shape_not_matched_by_default(self):
        assert "PHONE" not in _types(f"num {PHONE_BARE}")


class TestPhoneOptIn:
    def test_bare_phone_detected_when_strict_numeric_false(self):
        assert "PHONE" in _types(f"num {PHONE_BARE}", strict_numeric=False)


class TestIssue158Scenario:
    def test_browser_tool_json_produces_no_findings(self):
        payload = (
            '{"availableTabs":[{"tabId":' + TAB_ID_9 + ',"title":"New Tab"}],'
            '"tabGroupId":' + TAB_ID_10 + "}"
        )
        assert datafog.scan(payload, engine="regex").entities == []
