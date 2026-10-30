import pytest
from app.utils.validators import (
    parse_date, parse_amount, validate_date_sequence,
    validate_amounts, validate_file_type, validate_file_size
)


class TestDateParsing:
    def test_parse_date_yyyy_mm_dd(self):
        assert parse_date("2024-01-15") == "2024-01-15"
    
    def test_parse_date_dd_mm_yyyy(self):
        assert parse_date("15-01-2024") == "2024-01-15"
    
    def test_parse_date_mm_dd_yyyy(self):
        assert parse_date("01-15-2024") == "2024-01-15"
    
    def test_parse_date_slash_format(self):
        assert parse_date("01/15/2024") == "2024-01-15"
    
    def test_parse_date_invalid(self):
        assert parse_date("invalid-date") is None
    
    def test_parse_date_empty(self):
        assert parse_date("") is None

    def test_parse_date_full_month_name(self):
        assert parse_date("September 26, 2026") == "2026-09-26"

    def test_parse_date_month_name_without_comma(self):
        assert parse_date("Sep 26 2026") == "2026-09-26"

    def test_parse_date_day_first_full_month_name(self):
        assert parse_date("26 September 2026") == "2026-09-26"


class TestAmountParsing:
    def test_parse_amount_with_dollar(self):
        result = parse_amount("$1,250.00")
        assert result == (1250.00, "USD")
    
    def test_parse_amount_with_comma(self):
        result = parse_amount("1,250.00")
        assert result == (1250.00, "USD")
    
    def test_parse_amount_with_currency_code(self):
        result = parse_amount("1250.00 USD")
        assert result == (1250.00, "USD")
    
    def test_parse_amount_eur(self):
        result = parse_amount("€1,250.00")
        assert result == (1250.00, "EUR")
    
    def test_parse_amount_invalid(self):
        assert parse_amount("invalid") is None
    
    def test_parse_amount_empty(self):
        assert parse_amount("") is None


class TestDateSequenceValidation:
    def test_valid_date_sequence(self):
        assert validate_date_sequence("2024-01-01", "2024-01-30") is True
    
    def test_invalid_date_sequence(self):
        assert validate_date_sequence("2024-01-30", "2024-01-01") is False
    
    def test_same_dates(self):
        assert validate_date_sequence("2024-01-01", "2024-01-01") is True
    
    def test_invalid_dates(self):
        assert validate_date_sequence("invalid", "2024-01-01") is False


class TestAmountValidation:
    def test_valid_amounts(self):
        assert validate_amounts(100.00, 8.00, 108.00) is True
    
    def test_amounts_with_tolerance(self):
        assert validate_amounts(100.00, 8.00, 108.01, tolerance=0.02) is True
    
    def test_invalid_amounts(self):
        assert validate_amounts(100.00, 8.00, 200.00) is False
    
    def test_missing_subtotal(self):
        assert validate_amounts(None, 8.00, 108.00) is True  # Can't validate
    
    def test_missing_subtotal_tax_exceeds_total(self):
        assert validate_amounts(None, 50.00, 10.00) is False
    
    def test_negative_amounts(self):
        # This is handled separately, but the math validation should still work
        assert validate_amounts(-100.00, 8.00, -92.00) is True


class TestFileTypeValidation:
    def test_valid_pdf(self):
        assert validate_file_type("invoice.pdf", ["pdf", "png", "jpg"]) is True
    
    def test_valid_png(self):
        assert validate_file_type("invoice.png", ["pdf", "png", "jpg"]) is True
    
    def test_invalid_type(self):
        assert validate_file_type("invoice.docx", ["pdf", "png", "jpg"]) is False
    
    def test_case_insensitive(self):
        assert validate_file_type("invoice.PDF", ["pdf", "png", "jpg"]) is True
    
    def test_no_extension(self):
        assert validate_file_type("invoice", ["pdf", "png", "jpg"]) is False


class TestFileSizeValidation:
    def test_valid_size(self):
        assert validate_file_size(1024 * 1024, 10) is True  # 1MB, limit 10MB
    
    def test_size_exceeds_limit(self):
        assert validate_file_size(11 * 1024 * 1024, 10) is False  # 11MB, limit 10MB
    
    def test_exact_limit(self):
        assert validate_file_size(10 * 1024 * 1024, 10) is True  # Exactly 10MB
    
    def test_zero_size(self):
        assert validate_file_size(0, 10) is True
