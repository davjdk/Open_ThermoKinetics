"""
Test module for enhanced configuration functionality (Stage 2).

Tests the enhanced AggregationConfig with new parameters for
enhanced pattern detection and metadata management.
"""

from src.log_aggregator.config import AggregationConfig


class TestEnhancedAggregationConfig:
    """Test enhanced configuration functionality."""

    def test_default_config_enhanced_features(self):
        """Test that default config includes enhanced features."""
        config = AggregationConfig.default()

        assert config.enhanced_patterns_enabled is True
        assert config.pattern_type_priorities is not None
        assert config.pattern_time_windows is not None
        assert config.min_cascade_depth == 3
        assert config.max_pattern_metadata_size == 1000

    def test_pattern_type_priorities_default(self):
        """Test default pattern type priorities."""
        config = AggregationConfig.default()
        priorities = config.pattern_type_priorities

        # Check that all expected pattern types have priorities
        expected_types = [
            "plot_lines_addition",
            "cascade_component_initialization",
            "request_response_cycle",
            "file_operations",
            "gui_updates",
            "basic_similarity",
        ]

        for pattern_type in expected_types:
            assert pattern_type in priorities
            assert isinstance(priorities[pattern_type], int)

        # Check priority ordering (higher values = higher priority)
        assert priorities["plot_lines_addition"] > priorities["basic_similarity"]
        assert priorities["cascade_component_initialization"] > priorities["gui_updates"]

    def test_pattern_time_windows_default(self):
        """Test default pattern time windows."""
        config = AggregationConfig.default()
        time_windows = config.pattern_time_windows

        # Check that all pattern types have time windows
        expected_types = [
            "plot_lines_addition",
            "cascade_component_initialization",
            "request_response_cycle",
            "file_operations",
            "gui_updates",
            "basic_similarity",
        ]

        for pattern_type in expected_types:
            assert pattern_type in time_windows
            assert isinstance(time_windows[pattern_type], float)
            assert time_windows[pattern_type] > 0

    def test_enhanced_config_validation(self):
        """Test validation of enhanced configuration parameters."""
        # Test valid config
        config = AggregationConfig(enhanced_patterns_enabled=True, min_cascade_depth=3, max_pattern_metadata_size=1000)
        assert config.validate() is True

        # Test invalid min_cascade_depth
        config.min_cascade_depth = 1
        assert config.validate() is False

        # Reset to valid value
        config.min_cascade_depth = 3
        assert config.validate() is True

        # Test invalid max_pattern_metadata_size
        config.max_pattern_metadata_size = 0
        assert config.validate() is False

        # Test negative max_pattern_metadata_size
        config.max_pattern_metadata_size = -100
        assert config.validate() is False

    def test_minimal_config_with_enhanced_features(self):
        """Test minimal config includes enhanced features."""
        config = AggregationConfig.minimal()

        # Should still have enhanced features enabled by default
        assert config.enhanced_patterns_enabled is True
        assert config.pattern_type_priorities is not None
        assert config.pattern_time_windows is not None

    def test_custom_pattern_priorities(self):
        """Test custom pattern type priorities."""
        custom_priorities = {
            "plot_lines_addition": 10,
            "cascade_component_initialization": 5,
            "request_response_cycle": 1,
            "file_operations": 7,
            "gui_updates": 3,
            "basic_similarity": 0,
        }

        config = AggregationConfig(pattern_type_priorities=custom_priorities)

        assert config.pattern_type_priorities == custom_priorities
        assert config.validate() is True

    def test_custom_time_windows(self):
        """Test custom pattern time windows."""
        custom_windows = {
            "plot_lines_addition": 1.5,
            "cascade_component_initialization": 10.0,
            "request_response_cycle": 0.5,
            "file_operations": 15.0,
            "gui_updates": 0.1,
            "basic_similarity": 2.0,
        }

        config = AggregationConfig(pattern_time_windows=custom_windows)

        assert config.pattern_time_windows == custom_windows
        assert config.validate() is True

    def test_disabled_enhanced_patterns(self):
        """Test configuration with enhanced patterns disabled."""
        config = AggregationConfig(enhanced_patterns_enabled=False)

        assert config.enhanced_patterns_enabled is False
        # Should still have defaults for other enhanced features
        assert config.pattern_type_priorities is not None
        assert config.pattern_time_windows is not None
        assert config.validate() is True

    def test_post_init_none_values(self):
        """Test that None values are properly initialized in __post_init__."""
        config = AggregationConfig(pattern_type_priorities=None, pattern_time_windows=None)

        # Should be initialized with defaults
        assert config.pattern_type_priorities is not None
        assert config.pattern_time_windows is not None
        assert len(config.pattern_type_priorities) > 0
        assert len(config.pattern_time_windows) > 0

    def test_config_backward_compatibility(self):
        """Test that enhanced config is backward compatible with Stage 1."""
        # Should be able to create config with only Stage 1 parameters
        config = AggregationConfig(
            buffer_size=50,
            flush_interval=3.0,
            min_pattern_entries=3,
            pattern_similarity_threshold=0.7,
            max_processing_time=0.2,
            enabled=True,
            collect_statistics=True,
        )

        assert config.validate() is True
        assert config.buffer_size == 50
        assert config.flush_interval == 3.0
        # Enhanced features should still be available with defaults
        assert config.enhanced_patterns_enabled is True
