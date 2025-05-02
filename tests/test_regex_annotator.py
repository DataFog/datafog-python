from typing import Dict, List

import pytest

# Import the regex annotator module
from datafog.processing.text_processing.regex_annotator import (
    AnnotationResult,
    RegexAnnotator,
    Span,
)


# Fixtures for test data
@pytest.fixture
def sample_text():
    """Sample text containing various PII entities."""
    return (
        "Contact John Doe at john.doe@example.com or call (555) 123-4567. "
        "His SSN is 123-45-6789 and credit card 4111111111111111. "
        "He lives at 123 Main St, New York, NY 10001. "
        "His IP address is 192.168.1.1 and his birthday is 01/01/1980."
    )


@pytest.fixture
def expected_annotations():
    """Expected annotations for the sample text."""
    return {
        "EMAIL": ["john.doe@example.com"],
        "PHONE": ["(555) 123-4567"],
        "SSN": ["123-45-6789"],
        "CREDIT_CARD": ["4111111111111111"],
        "IP_ADDRESS": ["192.168.1.1"],
        "DOB": ["01/01/1980"],
        "ZIP": ["10001"],
    }


# Basic tests for the RegexAnnotator


def test_regex_annotator_initialization():
    """Test that the RegexAnnotator can be initialized."""
    annotator = RegexAnnotator()
    assert annotator is not None
    assert (
        len(annotator.LABELS) == 7
    )  # EMAIL, PHONE, SSN, CREDIT_CARD, IP_ADDRESS, DOB, ZIP


def test_regex_annotator_create_method():
    """Test the create factory method."""
    annotator = RegexAnnotator.create()
    assert annotator is not None
    assert isinstance(annotator, RegexAnnotator)


def test_empty_text_annotation():
    """Test that annotating empty text returns empty results."""
    annotator = RegexAnnotator()
    result = annotator.annotate("")
    assert result is not None
    assert isinstance(result, dict)
    assert all(len(entities) == 0 for entities in result.values())


# Tests for specific regex patterns


def test_email_regex():
    """Test the EMAIL regex pattern."""
    annotator = RegexAnnotator()

    # Test valid email formats
    valid_emails = [
        "user@example.com",
        "first.last@example.co.uk",
        "user+tag@example.org",
        "user-name@domain.com",
        "user123@domain-name.com",
    ]

    for email in valid_emails:
        result = annotator.annotate(f"Contact me at {email} for more information.")
        assert email in result["EMAIL"], f"Failed to detect valid email: {email}"

    # Test edge cases that should be detected
    edge_emails = [
        "a@b.co",  # Minimal valid email
        "very.unusual.@.unusual.com",  # Multiple dots
        "!#$%&'*+-/=?^_`{}|~@example.org",  # Special chars in local part
    ]

    for email in edge_emails:
        result = annotator.annotate(f"Contact: {email}")
        assert email in result["EMAIL"], f"Failed to detect edge case email: {email}"

    # Test invalid emails that should be rejected
    invalid_emails = [
        "plainaddress",  # Missing @ symbol
        "@missinglocal.org",  # Missing local part
        "user@",  # Missing domain
        "user@.com",  # Domain starts with dot
        "user@domain@domain.com",  # Multiple @ symbols
        "user@[123.456.789.000]",  # Invalid IP format in domain
    ]

    for email in invalid_emails:
        result = annotator.annotate(f"Invalid email: {email}")
        assert (
            email not in result["EMAIL"]
        ), f"Incorrectly detected invalid email: {email}"


def test_phone_regex():
    """Test the PHONE regex pattern."""
    annotator = RegexAnnotator()

    # Test valid phone formats (NANP - North American Numbering Plan)
    valid_phones = [
        "555-555-5555",
        "(555) 555-5555",
        "555.555.5555",
        "5555555555",
        "+1 555-555-5555",
        "+1 (555) 555-5555",
    ]

    for phone in valid_phones:
        result = annotator.annotate(f"Call me at {phone}")
        assert phone in result["PHONE"], f"Failed to detect valid phone: {phone}"

    # Test edge cases that should be detected
    edge_phones = [
        "555 555 5555",  # Spaces as separators
        "1-555-555-5555",  # Leading 1 without +
        "1.555.555.5555",  # Leading 1 with dots
    ]

    for phone in edge_phones:
        result = annotator.annotate(f"Phone: {phone}")
        assert phone in result["PHONE"], f"Failed to detect edge case phone: {phone}"

    # Test invalid phones that should be rejected
    invalid_phones = [
        "555-55-5555",  # Too few digits in second group
        "555-555-555",  # Too few digits in last group
        "(55) 555-5555",  # Too few digits in area code
        "5555-5555",  # Missing area code
        "555-555-55555",  # Too many digits in last group
    ]

    for phone in invalid_phones:
        result = annotator.annotate(f"Invalid phone: {phone}")
        assert (
            phone not in result["PHONE"]
        ), f"Incorrectly detected invalid phone: {phone}"


def test_ssn_regex():
    """Test the SSN regex pattern."""
    annotator = RegexAnnotator()

    # Test valid SSN formats
    valid_ssns = ["123-45-6789", "234-56-7890", "345-67-8901"]

    for ssn in valid_ssns:
        result = annotator.annotate(f"SSN: {ssn}")
        assert ssn in result["SSN"], f"Failed to detect valid SSN: {ssn}"

    # Test edge cases that should be detected
    edge_ssns = [
        "111-22-3333",  # Repeating digits but valid format
        "999-88-7777",  # High numbers but valid format
    ]

    for ssn in edge_ssns:
        result = annotator.annotate(f"Edge SSN: {ssn}")
        assert ssn in result["SSN"], f"Failed to detect edge case SSN: {ssn}"

    # Test invalid SSNs that should be rejected
    invalid_ssns = [
        "12-34-5678",  # Too few digits in first group
        "123-4-5678",  # Too few digits in second group
        "123-45-678",  # Too few digits in third group
        "1234-56-7890",  # Too many digits in first group
        "123456789",  # No hyphens
        "000-12-3456",  # Starts with 000 (invalid)
        "666-12-3456",  # Starts with 666 (invalid)
    ]

    for ssn in invalid_ssns:
        result = annotator.annotate(f"Invalid SSN: {ssn}")
        assert ssn not in result["SSN"], f"Incorrectly detected invalid SSN: {ssn}"


def test_credit_card_regex():
    """Test the CREDIT_CARD regex pattern."""
    annotator = RegexAnnotator()

    # Test valid credit card formats (Visa, Mastercard, Amex)
    valid_cards = [
        "4111111111111111",  # Visa (16 digits, starts with 4)
        "5555555555554444",  # Mastercard (16 digits, starts with 5)
        "378282246310005",  # American Express (15 digits, starts with 3)
    ]

    for card in valid_cards:
        result = annotator.annotate(f"Card: {card}")
        assert (
            card in result["CREDIT_CARD"]
        ), f"Failed to detect valid credit card: {card}"

    # Test edge cases that should be detected
    edge_cards = [
        "4111-1111-1111-1111",  # Visa with dashes
        "5555 5555 5555 4444",  # Mastercard with spaces
        "3782 822463 10005",  # Amex with irregular spacing
    ]

    for card in edge_cards:
        result = annotator.annotate(f"Edge card: {card}")
        assert (
            card in result["CREDIT_CARD"]
        ), f"Failed to detect edge case credit card: {card}"

    # Test invalid cards that should be rejected
    invalid_cards = [
        "411111111111111",  # Visa with 15 digits (too short)
        "41111111111111111",  # Visa with 17 digits (too long)
        "6111111111111111",  # Starts with 6 (not Visa, MC, or Amex)
        "abcdefghijklmnop",  # Non-numeric
        "1234567890123456",  # Starts with 1 (not Visa, MC, or Amex)
    ]

    for card in invalid_cards:
        result = annotator.annotate(f"Invalid card: {card}")
        assert (
            card not in result["CREDIT_CARD"]
        ), f"Incorrectly detected invalid credit card: {card}"


def test_ip_address_regex():
    """Test the IP_ADDRESS regex pattern."""
    annotator = RegexAnnotator()

    # Test valid IPv4 addresses
    valid_ipv4 = [
        "192.168.1.1",
        "10.0.0.1",
        "172.16.0.1",
        "127.0.0.1",
        "255.255.255.255",
    ]

    for ip in valid_ipv4:
        result = annotator.annotate(f"IPv4: {ip}")
        assert ip in result["IP_ADDRESS"], f"Failed to detect valid IPv4: {ip}"

    # Test valid IPv6 addresses
    valid_ipv6 = [
        "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
        "fe80::1ff:fe23:4567:890a",
        "2001:db8::ff00:42:8329",
    ]

    for ip in valid_ipv6:
        result = annotator.annotate(f"IPv6: {ip}")
        assert ip in result["IP_ADDRESS"], f"Failed to detect valid IPv6: {ip}"

    # Test invalid IP addresses that should be rejected
    invalid_ips = [
        "256.256.256.256",  # IPv4 with invalid octets > 255
        "192.168.1",  # IPv4 with missing octet
        "192.168.1.1.1",  # IPv4 with extra octet
        "300.168.1.1",  # IPv4 with invalid first octet
        "192.300.1.1",  # IPv4 with invalid second octet
        "2001:xyz::",  # IPv6 with invalid hex characters
        "123.123.123.123.123",  # Too many segments for IPv4
    ]

    for ip in invalid_ips:
        result = annotator.annotate(f"Invalid IP: {ip}")
        assert ip not in result["IP_ADDRESS"], f"Incorrectly detected invalid IP: {ip}"


def test_dob_regex():
    """Test the DOB (Date of Birth) regex pattern."""
    annotator = RegexAnnotator()

    # Test valid date formats
    valid_dates = [
        "01/01/1980",  # MM/DD/YYYY format
        "12/31/2000",  # MM/DD/YYYY format
        "1/1/1990",  # M/D/YYYY format
        "1980-01-01",  # YYYY-MM-DD format (ISO)
        "2000-12-31",  # YYYY-MM-DD format (ISO)
    ]

    for date in valid_dates:
        result = annotator.annotate(f"DOB: {date}")
        assert date in result["DOB"], f"Failed to detect valid date: {date}"

    # Test edge cases that should be detected
    edge_dates = [
        "01-01-1980",  # MM-DD-YYYY format with dashes
        "1-1-1990",  # M-D-YYYY format with dashes
    ]

    for date in edge_dates:
        result = annotator.annotate(f"Edge date: {date}")
        assert date in result["DOB"], f"Failed to detect edge case date: {date}"

    # Test invalid dates that should be rejected
    invalid_dates = [
        "13/01/2000",  # Invalid month > 12
        "01/32/2000",  # Invalid day > 31
        "00/00/0000",  # All zeros
        "01.01.2000",  # Invalid separator (dot)
        "2000/01/01",  # YYYY/MM/DD format (not in our spec)
        "01-01",  # Missing year
    ]

    for date in invalid_dates:
        result = annotator.annotate(f"Invalid date: {date}")
        assert date not in result["DOB"], f"Incorrectly detected invalid date: {date}"


def test_zip_regex():
    """Test the ZIP regex pattern."""
    annotator = RegexAnnotator()

    # Test valid ZIP code formats
    valid_zips = ["12345", "12345-6789"]  # Basic 5-digit ZIP  # ZIP+4 format

    for zip_code in valid_zips:
        result = annotator.annotate(f"ZIP: {zip_code}")
        assert zip_code in result["ZIP"], f"Failed to detect valid ZIP: {zip_code}"

    # Test edge cases that should be detected
    edge_zips = [
        "00000",  # All zeros but valid format
        "99999-9999",  # All nines but valid format
    ]

    for zip_code in edge_zips:
        result = annotator.annotate(f"Edge ZIP: {zip_code}")
        assert zip_code in result["ZIP"], f"Failed to detect edge case ZIP: {zip_code}"

    # Test invalid ZIPs that should be rejected
    invalid_zips = [
        "1234",  # Too few digits (4 instead of 5)
        "123456",  # Too many digits (6 instead of 5)
        "12345-123",  # ZIP+4 with too few digits in second part
        "12345-12345",  # ZIP+4 with too many digits in second part
        "ABCDE",  # Non-numeric characters
        "12345-ABCD",  # Non-numeric characters in second part
    ]

    for zip_code in invalid_zips:
        result = annotator.annotate(f"Invalid ZIP: {zip_code}")
        assert (
            zip_code not in result["ZIP"]
        ), f"Incorrectly detected invalid ZIP: {zip_code}"


def test_annotation_result_format():
    """Test the structured AnnotationResult format."""
    annotator = RegexAnnotator()

    # Test text with multiple entity types
    test_text = "Contact John at john@example.com or 555-123-4567. SSN: 123-45-6789."

    # Get both result formats
    dict_result, structured_result = annotator.annotate_with_spans(test_text)

    # Test dictionary format (backward compatibility)
    assert isinstance(dict_result, dict)
    assert "EMAIL" in dict_result
    assert "john@example.com" in dict_result["EMAIL"]
    assert "PHONE" in dict_result
    assert "555-123-4567" in dict_result["PHONE"]
    assert "SSN" in dict_result
    assert "123-45-6789" in dict_result["SSN"]

    # Test structured format
    assert isinstance(structured_result, AnnotationResult)
    assert structured_result.text == test_text
    assert len(structured_result.spans) >= 3  # At least email, phone, and SSN

    # Verify spans have correct information
    email_spans = [span for span in structured_result.spans if span.label == "EMAIL"]
    phone_spans = [span for span in structured_result.spans if span.label == "PHONE"]
    ssn_spans = [span for span in structured_result.spans if span.label == "SSN"]

    assert len(email_spans) >= 1
    assert email_spans[0].text == "john@example.com"
    assert email_spans[0].start == test_text.find("john@example.com")
    assert email_spans[0].end == test_text.find("john@example.com") + len(
        "john@example.com"
    )

    assert len(phone_spans) >= 1
    assert phone_spans[0].text == "555-123-4567"

    assert len(ssn_spans) >= 1
    assert ssn_spans[0].text == "123-45-6789"
