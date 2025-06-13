"""
Tests for AggregationConfig module.
"""

from src.log_aggregator.config import AggregationConfig


class TestAggregationConfig:
    """Test cases for AggregationConfig class."""

    def test_default_config_creation(self):
        """Test creating default configuration."""
        config = AggregationConfig.default()

        assert config.buffer_size == 1000
        assert config.flush_interval == 2.0
        assert config.min_pattern_entries == 3
        assert config.pattern_similarity_threshold == 0.8
        assert config.max_processing_time == 0.1
        assert config.enabled is True
        assert config.collect_statistics is True

    def test_minimal_config_creation(self):
        """Test creating minimal configuration."""
        config = AggregationConfig.minimal()

        assert config.buffer_size == 20
        assert config.flush_interval == 2.0
        assert config.min_pattern_entries == 2
        assert config.pattern_similarity_threshold == 0.9

    def test_custom_config_creation(self):
        """Test creating custom configuration."""
        config = AggregationConfig(
            buffer_size=50, flush_interval=3.0, min_pattern_entries=3, pattern_similarity_threshold=0.7, enabled=False
        )

        assert config.buffer_size == 50
        assert config.flush_interval == 3.0
        assert config.min_pattern_entries == 3
        assert config.pattern_similarity_threshold == 0.7
        assert config.enabled is False

    def test_config_validation_valid(self):
        """Test validation with valid configuration."""
        config = AggregationConfig.default()
        assert config.validate() is True

    def test_config_validation_invalid_buffer_size(self):
        """Test validation with invalid buffer size."""
        config = AggregationConfig(buffer_size=0)
        assert config.validate() is False

        config = AggregationConfig(buffer_size=-1)
        assert config.validate() is False

    def test_config_validation_invalid_flush_interval(self):
        """Test validation with invalid flush interval."""
        config = AggregationConfig(flush_interval=0)
        assert config.validate() is False

        config = AggregationConfig(flush_interval=-1)
        assert config.validate() is False

    def test_config_validation_invalid_min_pattern_entries(self):
        """Test validation with invalid min pattern entries."""
        config = AggregationConfig(min_pattern_entries=0)
        assert config.validate() is False

    def test_config_validation_invalid_similarity_threshold(self):
        """Test validation with invalid similarity threshold."""
        config = AggregationConfig(pattern_similarity_threshold=-0.1)
        assert config.validate() is False

        config = AggregationConfig(pattern_similarity_threshold=1.1)
        assert config.validate() is False

    def test_config_validation_invalid_processing_time(self):
        """Test validation with invalid processing time."""
        config = AggregationConfig(max_processing_time=0)
        assert config.validate() is False

        config = AggregationConfig(max_processing_time=-1)
        assert config.validate() is False
