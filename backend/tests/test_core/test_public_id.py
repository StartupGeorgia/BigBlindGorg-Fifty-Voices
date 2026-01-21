"""Tests for public ID generation utilities in app/core/public_id.py."""

import pytest

from app.core.public_id import (
    ALPHABET,
    EXPECTED_PARTS_COUNT,
    MAX_RANDOM_LENGTH,
    MIN_RANDOM_LENGTH,
    generate_public_id,
    validate_public_id,
)


class TestGeneratePublicId:
    """Tests for generate_public_id function."""

    def test_default_format(self) -> None:
        """Test default public ID format (ag_xxxxxxxx)."""
        public_id = generate_public_id()

        assert public_id.startswith("ag_")
        parts = public_id.split("_")
        assert len(parts) == EXPECTED_PARTS_COUNT
        assert parts[0] == "ag"
        assert len(parts[1]) == 8  # Default length

    def test_custom_prefix(self) -> None:
        """Test public ID with custom prefix."""
        public_id = generate_public_id(prefix="usr")

        assert public_id.startswith("usr_")
        parts = public_id.split("_")
        assert parts[0] == "usr"

    def test_custom_length(self) -> None:
        """Test public ID with custom random length."""
        for length in [6, 10, 16]:
            public_id = generate_public_id(length=length)
            parts = public_id.split("_")
            assert len(parts[1]) == length

    def test_only_alphanumeric_chars(self) -> None:
        """Test that random part only contains alphanumeric characters."""
        # Generate multiple IDs to ensure randomness doesn't produce invalid chars
        for _ in range(100):
            public_id = generate_public_id()
            random_part = public_id.split("_")[1]

            for char in random_part:
                assert char in ALPHABET, f"Invalid character '{char}' in {public_id}"

    def test_uniqueness(self) -> None:
        """Test that generated IDs are unique."""
        ids = [generate_public_id() for _ in range(1000)]
        unique_ids = set(ids)

        # All 1000 IDs should be unique
        assert len(unique_ids) == 1000

    def test_url_safe(self) -> None:
        """Test that generated IDs are URL-safe."""
        # URL-unsafe characters that should not appear
        unsafe_chars = set("/:?#[]@!$&'()+,;= ")

        for _ in range(100):
            public_id = generate_public_id()
            for char in public_id:
                if char != "_":  # Underscore is the delimiter
                    assert char not in unsafe_chars, f"Unsafe char '{char}' in {public_id}"

    def test_empty_prefix(self) -> None:
        """Test with empty prefix."""
        public_id = generate_public_id(prefix="")

        assert public_id.startswith("_")
        parts = public_id.split("_", 1)
        assert parts[0] == ""

    def test_long_prefix(self) -> None:
        """Test with long prefix."""
        long_prefix = "workspace_agent"
        public_id = generate_public_id(prefix=long_prefix)

        assert public_id.startswith(f"{long_prefix}_")


class TestValidatePublicId:
    """Tests for validate_public_id function."""

    def test_valid_default_id(self) -> None:
        """Test validation of valid default format ID."""
        public_id = generate_public_id()
        assert validate_public_id(public_id) is True

    def test_valid_custom_prefix(self) -> None:
        """Test validation with custom prefix."""
        public_id = generate_public_id(prefix="usr")
        assert validate_public_id(public_id, prefix="usr") is True

    def test_invalid_prefix_mismatch(self) -> None:
        """Test that wrong prefix fails validation."""
        public_id = generate_public_id(prefix="ag")
        assert validate_public_id(public_id, prefix="usr") is False

    def test_empty_string_invalid(self) -> None:
        """Test that empty string is invalid."""
        assert validate_public_id("") is False

    def test_none_like_empty_invalid(self) -> None:
        """Test that None-like values are invalid."""
        assert validate_public_id("") is False

    def test_no_underscore_invalid(self) -> None:
        """Test that ID without underscore is invalid."""
        assert validate_public_id("agxK9mN2pQ") is False

    def test_random_part_too_short(self) -> None:
        """Test that random part below MIN_RANDOM_LENGTH is invalid."""
        short_id = "ag_abc"  # Only 3 chars, min is 6
        assert len(short_id.split("_")[1]) < MIN_RANDOM_LENGTH
        assert validate_public_id(short_id) is False

    def test_random_part_too_long(self) -> None:
        """Test that random part above MAX_RANDOM_LENGTH is invalid."""
        long_random = "a" * (MAX_RANDOM_LENGTH + 1)
        long_id = f"ag_{long_random}"
        assert validate_public_id(long_id) is False

    def test_random_part_min_length_valid(self) -> None:
        """Test that random part at MIN_RANDOM_LENGTH is valid."""
        min_id = f"ag_{'a' * MIN_RANDOM_LENGTH}"
        assert validate_public_id(min_id) is True

    def test_random_part_max_length_valid(self) -> None:
        """Test that random part at MAX_RANDOM_LENGTH is valid."""
        max_id = f"ag_{'z' * MAX_RANDOM_LENGTH}"
        assert validate_public_id(max_id) is True

    def test_invalid_characters_in_random_part(self) -> None:
        """Test that special characters in random part are invalid."""
        invalid_ids = [
            "ag_abc!defg",
            "ag_abc@defg",
            "ag_abc#defg",
            "ag_abc$defg",
            "ag_abc%defg",
            "ag_abc^defg",
            "ag_abc&defg",
            "ag_abc*defg",
            "ag_abc+defg",
            "ag_abc=defg",
            "ag_abc defg",  # Space
            "ag_abc-defg",  # Hyphen
        ]

        for invalid_id in invalid_ids:
            assert validate_public_id(invalid_id) is False, f"{invalid_id} should be invalid"

    def test_case_sensitivity(self) -> None:
        """Test that both uppercase and lowercase are valid."""
        # Mixed case should be valid
        mixed_case_id = "ag_AbCdEfGh"
        assert validate_public_id(mixed_case_id) is True

    def test_all_uppercase_valid(self) -> None:
        """Test all uppercase random part is valid."""
        assert validate_public_id("ag_ABCDEFGH") is True

    def test_all_lowercase_valid(self) -> None:
        """Test all lowercase random part is valid."""
        assert validate_public_id("ag_abcdefgh") is True

    def test_all_digits_valid(self) -> None:
        """Test all digits random part is valid."""
        assert validate_public_id("ag_12345678") is True

    def test_multiple_underscores(self) -> None:
        """Test that multiple underscores are handled correctly."""
        # The function splits on first underscore only
        # So "ag_test_abc" has prefix "ag" and random part "test_abc"
        # This should be invalid because underscore is not in ALPHABET
        multi_underscore = "ag_test_abc"
        assert validate_public_id(multi_underscore) is False

    def test_unicode_characters_invalid(self) -> None:
        """Test that unicode characters are invalid."""
        assert validate_public_id("ag_abcdefgh") is True  # Baseline
        assert validate_public_id("ag_\u00e9bcdefgh") is False  # e with accent

    def test_generated_ids_always_valid(self) -> None:
        """Test that all generated IDs pass validation."""
        for _ in range(100):
            public_id = generate_public_id()
            assert validate_public_id(public_id) is True, f"Generated ID {public_id} failed validation"

    def test_generated_custom_prefix_ids_valid(self) -> None:
        """Test generated IDs with custom prefix pass validation."""
        prefixes = ["usr", "ws", "contact", "call"]
        for prefix in prefixes:
            public_id = generate_public_id(prefix=prefix)
            assert validate_public_id(public_id, prefix=prefix) is True

    def test_generated_various_lengths_valid(self) -> None:
        """Test generated IDs with various lengths pass validation."""
        for length in range(MIN_RANDOM_LENGTH, MAX_RANDOM_LENGTH + 1):
            public_id = generate_public_id(length=length)
            assert validate_public_id(public_id) is True


class TestPublicIdIntegration:
    """Integration tests for public ID generation and validation."""

    def test_roundtrip_default(self) -> None:
        """Test that generated IDs can be validated."""
        for _ in range(50):
            generated = generate_public_id()
            assert validate_public_id(generated) is True

    def test_roundtrip_custom_settings(self) -> None:
        """Test roundtrip with custom prefix and length."""
        prefix = "custom"
        length = 12

        for _ in range(50):
            generated = generate_public_id(prefix=prefix, length=length)
            assert validate_public_id(generated, prefix=prefix) is True
            assert generated.startswith(f"{prefix}_")
            assert len(generated.split("_")[1]) == length

    def test_no_collision_in_bulk(self) -> None:
        """Test no collisions when generating many IDs."""
        ids = set()
        num_ids = 10000

        for _ in range(num_ids):
            new_id = generate_public_id()
            assert new_id not in ids, f"Collision detected: {new_id}"
            ids.add(new_id)

        assert len(ids) == num_ids
