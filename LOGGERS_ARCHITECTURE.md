# Log Aggregation Architecture for solid-state-kinetics

## Architectural Principles

### Foundational Principles (LOG AGGREGATION ARCHITECTURAL MANIFEST)
- **Explicit Operation Boundaries**: Developers explicitly mark operation boundaries using `OperationLogger` API
- **Dual-mode Processing**: Supports both explicit operation tracking and legacy pattern-based aggregation
- **Real-time Metrics Collection**: Comprehensive metrics gathering with automatic data compression for large datasets
- **Multi-stage Processing Pipeline**: Hierarchical processing through buffer → pattern detection → aggregation → tabular formatting
- **Comprehensive Monitoring**: Integration of operation monitoring, performance tracking, and optimization analysis
- **Error Context Expansion**: Detailed error analysis with preceding operations context and actionable recommendations
- **Thread-safe Operations**: Concurrent access support for multi-threaded scientific computation environments
- **Modular Component Design**: Loosely coupled components with standardized interfaces for extensibility and maintainability

---

## Overall Log Aggregation System Architecture

The log aggregation system implements a **hybrid explicit-automatic processing architecture** with PyQt6 integration, providing **intelligent operation tracking** and **structured tabular output** for scientific computation analysis.

### Central Processing Pipeline

The system processes logs through a **6-stage pipeline** with integrated monitoring and explicit operation support:

```mermaid
graph TB
    subgraph "Explicit Operation Layer"
        OL[OperationLogger<br/>Explicit Boundaries]
        OC[OperationContext<br/>Metrics & State]
        API[log_operation()<br/>@operation Decorator]
    end
    
    subgraph "Input Layer"
        LR[LogRecord] 
        PL[Python Logging]
        BLR[BufferedLogRecord<br/>Enhanced Metadata]
    end
    
    subgraph "Monitoring Layer"
        OM[OperationMonitor<br/>Metrics Collection]
        PM[PerformanceMonitor<br/>System Resources]
        OPM[OptimizationMonitor<br/>Scientific Computing]
    end
    
    subgraph "Pattern & Aggregation Layer"
        PD[PatternDetector<br/>Similarity Detection]
        OA[OperationAggregator<br/>Cascade Detection]
        AE[AggregationEngine<br/>Core Logic]
    end
    
    subgraph "Output Processing Layer"
        OTB[OperationTableBuilder<br/>Structured Tables]
        TF[TabularFormatter<br/>ASCII Formatting]
        EE[ErrorExpansionEngine<br/>Context Analysis]
    end
    
    subgraph "Integration Layer"
        RH[AggregatingHandler<br/>Python Logging Integration]
        TARGET[Target Handlers<br/>File/Console Output]
    end
    
    OL --> OC
    API --> OL
    OC --> OM
    
    LR --> PL
    PL --> BLR
    BLR --> PD
    BLR --> OA
    BLR --> OM
    
    OM --> PM
    OM --> OPM
    
    PD --> AE
    OA --> AE
    AE --> OTB
    OTB --> TF
    
    BLR --> EE
    TF --> RH
    EE --> RH
    RH --> TARGET
```
    
    subgraph "Monitoring Components"
        OM[OptimizationMonitor<br/>Long-running Processes]
        PM[PerformanceMonitor<br/>System Metrics]
        OPM[OperationMonitor<br/>Request Tracking]
    end
    
    LR --> BM
    BM --> BR
    BR --> PD
    PD --> LP
    LP --> PG
    PG --> AE
    AE --> ALR
    ALR --> TF### Processing Flow Integration

**Explicit Operation Flow**:
1. Developer marks operation boundaries using `@operation` decorator or `log_operation()` context manager
2. `OperationLogger` creates unique operation contexts with automatic metrics collection
3. `OperationMonitor` tracks performance metrics and scientific computation parameters
4. `OperationTableBuilder` converts operation metrics into structured tabular data
5. `TabularFormatter` renders tables as formatted ASCII for log output

**Legacy Pattern-based Flow**:
1. Log records are buffered in `BufferManager` with time/size-based flushing
2. `PatternDetector` identifies similar messages and groups them
3. `OperationAggregator` detects request-response cycles and operation cascades
4. `AggregationEngine` creates summary records from detected patterns
5. Output formatted through `TabularFormatter` and `ErrorExpansionEngine`

**Monitoring Integration**:
- `PerformanceMonitor` - System resource tracking (CPU, memory)
- `OptimizationMonitor` - Scientific computation analysis (MSE, convergence)
- All monitors feed into unified `OperationMonitor` for centralized metrics

### Integration Points

**Python Logging System Integration** (`src/log_aggregator/realtime_handler.py:20-468`):
- `AggregatingHandler` extends `logging.Handler` for seamless integration
- Compatible with existing `LoggerManager` infrastructure
- Configurable component activation through feature flags
- Pass-through capability for non-aggregated logging

**Configuration-driven Activation**:
```python
LoggerManager.configure_logging(
    enable_aggregation=True,
    aggregation_config={
        "buffer_size": 50, 
        "flush_interval": 3.0,
        "enable_operation_aggregation": True,
        "enable_tabular_formatting": True,
        "enable_error_expansion": True
    }
)
```

---

## Core Component Architecture

### Explicit Operation Tracking System

**OperationLogger** (`src/log_aggregator/operation_logger.py:90-528`) - **primary API for explicit operation boundaries**:

**Core API Methods**:
```python
class OperationLogger:
    def start_operation(self, operation_name: str) -> str  # Returns unique operation_id
    def end_operation(self, operation_id: Optional[str] = None, status: str = "SUCCESS")
    def add_metric(self, key: str, value: Any)  # Automatic data compression
    
# Context manager and decorator support
@log_operation("DECONVOLUTION")
def perform_deconvolution():
    operation_logger.add_metric("reactions_found", 3)
    
with log_operation("DATA_PROCESSING"):
    operation_logger.add_metric("data_shape", large_array.shape)
```

**Data Compression Features**:
- **Automatic compression** for large numpy arrays, pandas DataFrames, and dictionaries
- **Preview generation** for compressed data with statistical summaries
- **Configurable thresholds** through `DataCompressionConfig`
- **Integration with former ValueAggregator functionality**

**Thread-safe Operation Context**:
- Thread-local operation stacks for nested operations
- Automatic parent-child relationship tracking
- Integration with `OperationMonitor` for enhanced metrics

### Buffer Management System

**BufferManager** (`src/log_aggregator/buffer_manager.py:30-170`) - **thread-safe log record buffering**:

**Container Structure**:
- `BufferedLogRecord` - Enhanced `LogRecord` with metadata and timestamps
- `collections.deque` - Thread-safe circular buffer implementation
- Automatic processing state tracking and request ID detection

**Flushing Mechanisms**:
- **Size-based**: Configurable `max_size` threshold (default: 100 records)
- **Time-based**: Configurable `flush_interval` (default: 5.0 seconds)
- **Manual flushing**: On-demand processing trigger
- **Thread-safe operations**: `threading.Lock` for concurrent access

### Advanced Pattern Detection System

**PatternDetector** (`src/log_aggregator/pattern_detector.py:90-478`) - **intelligent message grouping with enhanced pattern types**:

**Supported Pattern Types**:
- `plot_lines_addition` - Matplotlib line additions for visualization tracking
- `cascade_component_initialization` - Component initialization sequences
- `request_response_cycle` - Request-response pairs with timing analysis  
- `file_operations` - File I/O operations with path and status tracking
- `gui_updates` - GUI component updates and state changes
- `basic_similarity` - Fallback pattern for general message similarity

**Pattern Analysis**:
```python
class PatternDetector:
    def detect_patterns(self, records: List[BufferedLogRecord]) -> List[Union[LogPattern, PatternGroup]]
    def _detect_specialized_patterns(self, records) -> List[PatternGroup]  # Enhanced patterns
    def _detect_basic_similarity_patterns(self, records) -> List[LogPattern]  # Fallback
```

**Enhanced Metadata Extraction**:
- **GUI components** extracted from Qt-related log messages
- **File paths and operations** detected from file system logs
- **Request IDs** parsed for operation correlation
- **Performance metrics** extracted from scientific computation logs

### Operation Aggregation System

**OperationAggregator** (`src/log_aggregator/operation_aggregator.py:50-670`) - **cascade detection and operation grouping**:**Dual-mode Operation Support**:
- **Explicit mode**: Works with `OperationLogger` for marked operation boundaries
- **Automatic mode**: Detects operation cascades from `handle_request_cycle` patterns
- **Cascade detection**: Groups related operations by timing and component relationships
- **Request-response correlation**: Matches requests with their corresponding responses

**Operation Group Structure**:
```python
@dataclass  
class OperationGroup:
    root_operation: str          # Initiating operation name
    start_time: datetime         # Cascade start timestamp
    end_time: datetime          # Cascade completion timestamp
    operation_count: int        # Number of operations in cascade
    actors: Set[str]            # Components involved
    operations: List[str]       # Chronological operation list
    request_ids: Set[str]       # Request correlation IDs
    has_errors: bool           # Error status flag
```

**Integration Features**:
- **Thread-safe operation tracking** with automatic timeout handling
- **Component relationship mapping** through actor analysis
- **Explicit operation boundaries** from `OperationLogger` integration
- **Cascade window management** for operation grouping

### Comprehensive Monitoring System

**OperationMonitor** (`src/log_aggregator/operation_monitor.py:80-734`) - **enhanced operation metrics collection**:

**Core Metrics Tracking**:
```python
@dataclass
class OperationMetrics:
    operation_id: str                    # Unique operation identifier
    operation_type: str                  # Type (DECONVOLUTION, MODEL_FIT, etc.)
    module: str                         # Executing module/component
    start_time: datetime                # Operation start timestamp
    duration_ms: Optional[float]        # Execution duration
    status: OperationStatus             # PENDING/RUNNING/COMPLETED/FAILED/TIMEOUT
    
    # Enhanced Stage 3 metrics
    request_count: int = 0              # Number of requests made
    response_count: int = 0             # Number of responses received  
    warning_count: int = 0              # Warnings encountered
    error_count: int = 0                # Errors encountered
    custom_metrics: Dict[str, Any]      # Domain-specific metrics
    components_involved: Set[str]       # Participating components
    sub_operations: List[str]           # Detected sub-operations
    memory_usage_mb: Optional[float]    # Memory consumption
```

**Scientific Computing Integration**:
- **Automatic metric extraction** from scientific computation logs
- **Performance correlation** with system resource usage
- **Operation timeout detection** with configurable thresholds
- **Hierarchical operation tracking** for nested operations

**PerformanceMonitor** (`src/log_aggregator/performance_monitor.py`) - **system resource tracking**:
- **CPU usage monitoring** during operations
- **Memory consumption tracking** with trend analysis
- **I/O operation metrics** for file-intensive processes
- **Performance correlation** with operation success rates

**OptimizationMonitor** (`src/log_aggregator/optimization_monitor.py`) - **scientific computation analysis**:
- **Convergence tracking** for optimization algorithms
- **MSE and R² analysis** for model fitting operations
- **Iteration counting** and convergence rate calculation
- **Parameter sensitivity analysis** for scientific algorithms

---

## Advanced Output Processing Architecture

### Structured Table Generation System

**OperationTableBuilder** (`src/log_aggregator/operation_table_builder.py:35-535`) - **conversion of metrics to tabular format**:
    first_seen: float     # Initial detection timestamp
    last_seen: float      # Latest occurrence timestamp
```

**Adaptive Column Selection**:
```python
class OperationTableBuilder:
    BASE_COLUMNS = [
        "Sub-Operation",    # Operation name/type
        "Start Time",       # Time stamp (HH:MM:SS)
        "Duration (s)",     # Execution duration
        "Component",        # Executing component
        "Status",          # Status with icons (✅/❌/⚠️)
    ]
    
    OPTIONAL_COLUMNS = {
        "request_count": "Requests",
        "mse_value": "MSE", 
        "r_squared": "R²",
        "file_count": "Files",
        "reaction_count": "Reactions",
        "heating_rates": "Heat Rates",
        "cpu_usage_avg": "CPU %",
        "memory_usage_mb": "Memory MB",
        "convergence_value": "Convergence",
        "iterations": "Iterations"
    }
```

**Table Types and Specialization**:
- **operation_summary**: General operation overview with timing and status
- **metrics_detail**: Detailed scientific metrics (MSE, R², convergence)
- **performance_metrics**: System performance data (CPU, memory, I/O)
- **domain_specific**: Specialized tables for scientific computing workflows

**Smart Data Formatting**:
- **Duration formatting**: Automatic ms/s/min selection based on magnitude
- **Scientific notation**: Proper formatting for small/large scientific values
- **Status icons**: Visual status indicators (✅ success, ❌ error, ⚠️ warning)
- **Adaptive precision**: Context-dependent decimal places for metrics

### Tabular Formatting System

**TabularFormatter** (`src/log_aggregator/tabular_formatter.py:50-703`) - **ASCII table rendering with specialized formatting**:

**Multi-format Support**:
```python
class TabularFormatter:
    def format_patterns_as_tables(self, patterns) -> List[BufferedLogRecord]
    def format_operation_table(self, table_data: OperationTableData) -> str
    def _format_ascii_table(self, table_data: TableData) -> str
    def _calculate_column_widths(self, headers, rows) -> List[int]
```

**Specialized Pattern Formatters**:
- `plot_lines_addition` - Matplotlib operations with component and timing data
- `request_response_cycle` - Request-response pairs with latency analysis
- `file_operations` - File I/O operations with path and status tracking
- `gui_updates` - GUI component updates with state change information
- `operation_summary` - **Explicit operation tables from OperationTableBuilder**

**Advanced Table Features**:
- **Adaptive column widths** based on content length
- **Header/separator styling** with configurable ASCII art
- **Summary row generation** with aggregate statistics
- **Unicode support** for scientific symbols and status indicators
- **Configurable table styling** through `TabularFormattingConfig`

### Aggregation Processing Engine

**AggregationEngine** (`src/log_aggregator/aggregation_engine.py:70-511`) - **pattern aggregation with enhanced monitoring**:

**Core Aggregation Logic**:
- **Minimum threshold enforcement**: Configurable `min_pattern_entries`
- **Time span calculation**: Duration between first and last occurrences
- **Sample message extraction**: Representative message selection
- **Statistical summarization**: Count, frequency, and temporal metrics

**Integrated Monitoring Architecture**:
- **OptimizationMonitor**: Tracks long-running scientific calculations
- **PerformanceMonitor**: System resource and processing metrics
- **OperationMonitor**: Request-response cycle and operation flow analysis
- **Cross-monitor correlation**: Links performance metrics with operation success rates

**Enhanced Output Structure**:
```python
@dataclass
class AggregatedLogRecord:
    pattern_id: str
    template: str
    count: int
    level: str
    logger_name: str
    first_timestamp: datetime
    last_timestamp: datetime
    sample_messages: List[str]
    
    def to_log_message(self) -> str  # Formatted summary output
    def to_dict(self) -> Dict[str, Any]  # Structured data for analysis
```

---

## Advanced Analysis Components

### Error Context Expansion Engine

**ErrorExpansionEngine** (`src/log_aggregator/error_expansion.py:90-557`) - **comprehensive error analysis with context**:

**Error Classification System**:
- **Automated pattern matching**: Keyword-based error categorization with domain-specific rules
- **Context analysis**: Preceding and following log record examination (configurable time window)
- **Operation correlation**: Links errors to specific operations through request ID tracking
- **Root cause investigation**: Traces operation chains leading to failures
- **Actionable recommendations**: Context-aware resolution suggestions

**Error Categories with Domain-specific Classification**:
- `file_not_found` - File system and data loading issues
- `memory_error` - Resource allocation and large dataset problems
- `optimization_failure` - Scientific calculation convergence failures
- `gui_error` - User interface exceptions and Qt-related issues
- `communication_error` - Inter-component failures and signal/slot problems
- `data_validation_error` - Scientific data integrity and format issues
- `calculation_timeout` - Long-running computation timeout failures

**Enhanced Context Structure**:
```python
@dataclass
class ErrorContext:
    error_record: BufferedLogRecord           # Original error record
    preceding_records: List[BufferedLogRecord] # Context before error
    following_records: List[BufferedLogRecord] # Aftermath records
    related_operations: List[BufferedLogRecord] # Same operation/component
    error_trace: Optional[str]                # Extracted stack trace
    suggested_actions: List[str]              # Resolution recommendations
    error_classification: Optional[str]       # Error category
    context_keywords: List[str]               # Extracted context keywords
```

**Advanced Analysis Features**:
- **Temporal context window**: Configurable time range (default: 5.0 seconds)
- **Operation correlation**: Links errors to specific operations via request/operation IDs
- **Stack trace extraction**: Automatic Python traceback parsing and formatting
- **Adaptive thresholds**: Load-based error expansion control (disable on high load)
- **Context keyword extraction**: Automatic identification of relevant terms for analysis
- **Rate limiting**: Maximum expansions per minute to prevent log flooding

---

## Configuration and Integration Architecture

### Comprehensive Configuration System

**AggregationConfig** (`src/log_aggregator/config.py:50-607`) - **centralized configuration management**:
- **Optimization progress**: Real-time calculation status tables
- **Error analysis**: Structured error context presentation
- **Performance metrics**: System resource utilization tables

**Configuration Options**:
```python
@dataclass
class TabularFormattingConfig:
    enabled: bool = True
    max_column_width: int = 50
    show_timestamps: bool = True
    show_loggers: bool = True
    compact_mode: bool = False
    table_borders: bool = True
```

---

## Specialized Monitoring Systems

### Optimization Process Monitoring

**OptimizationMonitor** (`src/log_aggregator/optimization_monitor.py:50-467`) - **long-running calculation tracking**:

**Process Status Tracking**:
```python
class OptimizationStatus(Enum):
    STARTING = "starting"
    RUNNING = "running"
    CONVERGING = "converging"
    STUCK = "stuck"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

**Metrics Collection**:
- **Iteration tracking**: Current vs. maximum iterations
- **Convergence analysis**: Progress rate and stagnation detection
- **Resource monitoring**: Memory usage and CPU utilization
- **Time estimation**: Completion time prediction

**Scientific Calculation Support**:
- **Deconvolution monitoring**: Peak fitting optimization progress
- **Model-based analysis**: Multi-reaction scheme optimization
- **Series analysis**: Batch processing status
- **Error propagation**: Optimization failure analysis

### Performance Metrics System

**Component Configuration Structure**:
```python
@dataclass
class AggregationConfig:
    # Buffer management settings
    buffer_size: int = 100                      # Maximum buffer size before flush
    flush_interval: float = 5.0                 # Automatic flush interval (seconds)
    
    # Pattern detection configuration
    pattern_similarity_threshold: float = 0.8   # Message similarity threshold
    min_pattern_entries: int = 2                # Minimum records for pattern creation
    
    # Feature enable/disable flags
    error_expansion_enabled: bool = True        # Error context expansion
    tabular_formatting_enabled: bool = True    # ASCII table generation
    operation_aggregation_enabled: bool = True # Operation cascade detection
    
    # Error expansion settings
    error_threshold_level: str = "ERROR"       # Minimum level for error expansion
    error_context_lines: int = 3               # Context lines around errors
    error_trace_depth: int = 10                # Maximum trace depth
    error_context_time_window: float = 5.0     # Context time window (seconds)
    
    # Monitoring configuration
    enable_optimization_monitoring: bool = True # Scientific computation tracking
    enable_performance_monitoring: bool = True  # System resource monitoring
    enable_operation_monitoring: bool = True    # Operation flow tracking
    
    # Sub-configurations
    tabular_formatting: Optional[TabularFormattingConfig] = None
    error_expansion: Optional[ErrorExpansionConfig] = None
    operation_aggregation: Optional[OperationAggregationConfig] = None
```

**Specialized Sub-configurations**:

**TabularFormattingConfig**:
```python
@dataclass
class TabularFormattingConfig:
    enabled: bool = True
    table_width_limit: int = 120               # Maximum table width
    column_padding: int = 1                    # Column padding spaces
    header_separator: str = "="                # Header separator character
    enable_unicode: bool = True                # Unicode symbol support
    timestamp_format: str = "%H:%M:%S"         # Time display format
    float_precision: int = 3                   # Decimal places for floats
```

**ErrorExpansionConfig**:
```python
@dataclass
class ErrorExpansionConfig:
    enabled: bool = True
    immediate_expansion: bool = True           # Expand errors immediately
    context_lines: int = 3                     # Lines of context to include
    save_context: bool = False                 # Save context to disk
    trace_depth: int = 10                      # Maximum trace analysis depth
    context_time_window: float = 5.0          # Context time window (seconds)
    adaptive_threshold: bool = True            # Adaptive behavior based on load
    disable_on_high_load: bool = True          # Disable during high system load
    max_expansions_per_minute: int = 10       # Rate limiting
```

**OperationAggregationConfig**:
```python
@dataclass
class OperationAggregationConfig:
    enabled: bool = True
    explicit_mode: bool = True                 # Support explicit operation boundaries
    cascade_detection: bool = True             # Detect operation cascades
    cascade_window: float = 2.0               # Time window for cascade detection
    min_cascade_operations: int = 2           # Minimum operations for cascade
    request_response_correlation: bool = True  # Correlate requests/responses
    operation_timeout: float = 30.0          # Operation timeout (seconds)
```

### Integration with LoggerManager

**Seamless Integration** (`src/log_aggregator/realtime_handler.py:40-468`):

```python
def configure_logging_with_aggregation():
    """Example configuration for enabling log aggregation."""
    LoggerManager.configure_logging(
        enable_aggregation=True,
        aggregation_config={
            "buffer_size": 50,
            "flush_interval": 3.0,
            "enable_error_expansion": True,
            "enable_tabular_formatting": True,
            "enable_operation_aggregation": True,
            "pattern_similarity_threshold": 0.85,
            "error_threshold_level": "WARNING"
        }
    )
```

**Optional Component Activation**:
- **AggregatingHandler** extends existing logging infrastructure
- **Feature flags** allow selective component activation
- **Configuration inheritance** from global logger settings
- **Runtime reconfiguration** support for dynamic adjustment

---

## Performance and Monitoring Architecture

### Multi-layer Monitoring System

**PerformanceMonitor** (`src/log_aggregator/performance_monitor.py`) - **system resource tracking**:
    error_threshold_level: str = "ERROR"
    error_context_lines: int = 3
    error_trace_depth: int = 10
    
    # Tabular formatting
    tabular_formatting_enabled: bool = True
    
    # Performance tuning
    enable_optimization_monitoring: bool = True
    enable_performance_monitoring: bool = True
    enable_operation_monitoring: bool = True
```

**Specialized Configurations**:
- **ErrorExpansionConfig**: Error analysis parameters
- **TabularFormattingConfig**: Table generation settings
- **OptimizationMonitoringConfig**: Long-running process settings
- **PerformanceMonitoringConfig**: System metrics parameters

### Safe Message Processing

**SafeMessageUtils** (`src/log_aggregator/safe_message_utils.py`) - **robust message handling**:

**Error-resistant Processing**:
- **Exception handling**: Graceful degradation for malformed records
- **Message normalization**: Consistent formatting across components
- **Encoding safety**: Unicode and special character handling
- **Comparison utilities**: Safe string comparison for pattern matching

---

## Data Flow and Processing Pipeline

### Real-time Processing Workflow

**Stage 1: Log Record Ingestion**
1. **Python logging event** → `AggregatingHandler.emit()`
2. **Record validation** → Safe message extraction
**Resource Monitoring Categories**:
- **Processing latency**: Log processing time measurements and trend analysis
- **Memory utilization**: Buffer memory, pattern cache, and system memory tracking
- **Throughput analysis**: Records processed per second with historical trending
- **Resource bottlenecks**: CPU, memory, and I/O constraint identification
- **System adaptation**: Automatic configuration adjustment based on load

**Adaptive Performance Behavior**:
- **Load-based throttling**: Automatic aggregation frequency adjustment
- **Memory pressure handling**: Dynamic buffer size optimization
- **Performance alerting**: Threshold-based notifications and warnings
- **Resource-aware operation**: Disables heavy processing during high system load

**OptimizationMonitor** (`src/log_aggregator/optimization_monitor.py`) - **scientific computation analysis**:

**Scientific Metrics Tracking**:
- **Convergence monitoring**: Optimization algorithm progress tracking
- **Iteration counting**: Step-by-step optimization process analysis
- **MSE and R² tracking**: Model fitting quality assessment
- **Parameter sensitivity**: Analysis of parameter changes during optimization
- **Algorithm performance**: Comparison of different optimization methods

**Integration with Scientific Workflows**:
- **Automatic detection** of optimization processes from log patterns
- **Real-time progress reporting** with convergence rate calculation
- **Performance correlation** between algorithm parameters and results
- **Historical analysis** of optimization performance across runs

### Operation Lifecycle Monitoring

**OperationMonitor** (`src/log_aggregator/operation_monitor.py:90-734`) - **comprehensive operation tracking**:

**Enhanced Operation Tracking**:
- **Explicit operation boundaries** from `OperationLogger` integration
- **Request correlation**: Matching requests to responses through request IDs
- **Latency measurement**: End-to-end operation timing with sub-operation breakdown
- **Success rate monitoring**: Operation completion statistics with failure analysis
- **Error correlation**: Linking failures to specific operations and components
- **Memory tracking**: Memory usage per operation with leak detection

**Advanced Integration Features**:
- **BaseSignals integration**: Automatic operation detection from signal emissions
- **Path-keys correlation**: Data operation tracking through hierarchical addressing
- **GUI interaction monitoring**: User action consequence tracking
- **Component relationship mapping**: Understanding inter-component dependencies
- **Timeout handling**: Automatic detection and handling of long-running operations

---

## Operational Data Flow Architecture

### End-to-End Processing Pipeline

**Stage 1: Input Capture and Buffering**
1. **Log record generation** → Python logging system
2. **Handler interception** → `AggregatingHandler.emit()`
3. **Buffer addition** → `BufferManager.add_record()` with thread safety
4. **Threshold checking** → Time/size-based flush triggers with load balancing

**Stage 2: Pattern Detection and Classification**
1. **Buffered records retrieval** → `BufferManager.get_pending_records()`
2. **Multi-pattern analysis** → `PatternDetector.detect_patterns()` with specialized algorithms
3. **Template extraction** → Variable placeholder identification and normalization
4. **Pattern classification** → Type-specific categorization (GUI, file ops, etc.)

**Stage 3: Operation and Aggregation Processing**
1. **Operation correlation** → `OperationAggregator` cascade detection and grouping
2. **Explicit operation integration** → `OperationLogger` boundary processing
3. **Metrics collection** → `OperationMonitor` comprehensive metrics gathering
4. **Statistical aggregation** → Count, timing, and sample generation

**Stage 4: Context Enhancement and Analysis**
1. **Error detection** → Log level and keyword analysis
2. **Context expansion** → `ErrorExpansionEngine.expand_error()` with temporal analysis
3. **Recommendation generation** → Context-aware actionable suggestion creation
4. **Operation correlation** → Linking errors to specific operations and workflows

**Stage 5: Table Generation and Output Formatting**
1. **Format selection** → Tabular vs. linear output decision based on content type
2. **Table generation** → `OperationTableBuilder` for operation metrics
3. **ASCII formatting** → `TabularFormatter.format_pattern()` with adaptive layout
4. **Final output** → Target handler forwarding with logging system integration

**Stage 6: Monitoring and Performance Analysis**
1. **Performance metrics collection** → System resource and processing time tracking
2. **Optimization analysis** → Scientific computation performance evaluation
3. **Adaptive configuration** → Dynamic adjustment based on system load
4. **Historical tracking** → Long-term performance trend analysis

### Explicit Operation Data Flow

**Operation Logger Flow**:
1. **Operation start** → `OperationLogger.start_operation()` creates context
2. **Metrics addition** → `add_metric()` with automatic data compression
3. **Sub-operation detection** → Automatic nesting through thread-local stacks
4. **Operation completion** → `end_operation()` finalizes metrics and timing
5. **Table generation** → `OperationTableBuilder` creates structured output

**Monitoring Integration Flow**:
1. **Monitor initialization** → `OperationMonitor.start_operation_tracking()`
2. **Real-time metrics** → Continuous collection during operation execution
3. **Resource correlation** → Links operation performance with system resources
4. **Completion analysis** → Success/failure determination with context analysis

---

## Integration with Core Application Architecture

### LoggerManager Integration

**Seamless Configuration Integration**:

**Seamless Integration Points**:
- **Optional activation**: Feature flag-based enabling
- **Configuration inheritance**: LoggerManager settings propagation
- **Handler chaining**: Existing logging infrastructure preservation
- **Performance impact**: Minimal overhead when disabled

**Configuration Integration**:
```python
# In LoggerManager.configure_logging()
if enable_aggregation:
    aggregating_handler = AggregatingHandler(
        target_handler=existing_handler,
        config=aggregation_config
    )
    logger.addHandler(aggregating_handler)
```

### Scientific Workflow Integration

**Domain-specific Pattern Recognition**:
- **Deconvolution operations**: Peak fitting progress tracking
- **Model-based calculations**: Multi-reaction optimization monitoring
- **Series analysis**: Batch processing status
- **GUI interactions**: User workflow tracking

**Kinetica Domain Integration**:
- **Reaction parameter updates**: Path-keys based operation tracking
- **Optimization convergence**: Scientific algorithm monitoring
- **Data loading operations**: File I/O pattern recognition
- **Error correlation**: Scientific calculation failure analysis

---

## Architectural Advantages

### Scalability and Performance
1. **Streaming processing**: Real-time log analysis without blocking
2. **Memory efficiency**: Bounded buffer sizes with automatic flushing
3. **Adaptive thresholds**: Load-based configuration adjustment
4. **Parallel processing**: Thread-safe components for concurrent access

### Maintainability and Extensibility
1. **Modular design**: Independent component development and testing
2. **Configuration-driven behavior**: Runtime customization without code changes
3. **Pattern extensibility**: Easy addition of new pattern types
4. **Monitoring expansion**: Pluggable monitoring component architecture

### Scientific Computing Focus
1. **Domain-aware patterns**: Scientific calculation-specific pattern recognition
2. **Optimization monitoring**: Long-running process tracking
3. **Error context analysis**: Comprehensive failure investigation
4. **Performance optimization**: Resource-conscious design for compute-intensive applications

### Development and Debugging Support
1. **Comprehensive error expansion**: Detailed failure analysis with recommendations
2. **Operation correlation**: Request-response lifecycle tracking
3. **Performance insights**: System bottleneck identification
4. **Structured output**: Machine-readable and human-friendly formats

The log aggregation architecture provides a comprehensive, intelligent logging infrastructure specifically designed for scientific computing applications, offering real-time insights, performance monitoring, and detailed error analysis while maintaining minimal overhead and seamless integration with existing systems.

```python
# Existing LoggerManager integration
LoggerManager.configure_logging(
    log_level="INFO",
    enable_aggregation=True,
    aggregation_config={
        "buffer_size": 50,
        "flush_interval": 3.0,
        "enable_error_expansion": True,
        "enable_tabular_formatting": True,
        "enable_operation_aggregation": True,
        "pattern_similarity_threshold": 0.85
    }
)

# Automatic handler integration
logger = LoggerManager.get_logger("solid_state_kinetics.calculations")
# All logs are automatically processed by AggregatingHandler
```

**Component Compatibility**:
- **Backward compatibility**: All existing logging continues to work without modification
- **Optional activation**: Aggregation can be enabled/disabled without code changes
- **Performance neutral**: Minimal overhead when aggregation is disabled
- **Configuration inheritance**: Aggregation settings inherit from global logger config

### BaseSignals Integration

**Automatic Operation Detection**:
```python
# Operations are automatically detected from BaseSignals emissions
def handle_request_cycle(self, target: str, operation: OperationType, **kwargs):
    # AggregatingHandler automatically detects this as an operation
    response = self.dispatch_request(target, operation, **kwargs)
    return response
```

**Path-keys Integration**:
- **Automatic detection** of path_keys in log messages for data operation correlation
- **Hierarchical tracking** of data access patterns through path_keys analysis
- **Component interaction mapping** through path_keys-based operation relationships

---

## Practical Usage Patterns and Examples

### Explicit Operation Logging Examples

**Basic Operation Tracking**:
```python
from src.log_aggregator import log_operation, operation_logger

# Context manager approach
@log_operation("DECONVOLUTION")
def perform_deconvolution(file_data):
    operation_logger.add_metric("file_name", file_data.name)
    operation_logger.add_metric("reactions_found", 3)
    operation_logger.add_metric("final_mse", 0.0123)
    # ... deconvolution logic ...
    return results

# Decorator approach  
@operation("MODEL_FIT_CALCULATION")
def calculate_model_fit(series_data):
    operation_logger.add_metric("fit_method", "Coats-Redfern")
    operation_logger.add_metric("reactions_analyzed", len(series_data.reactions))
    # ... calculation logic ...
    return fit_results
```

**Advanced Metrics Collection**:
```python
# Scientific computation with automatic data compression
with log_operation("OPTIMIZATION_PROCESS"):
    operation_logger.add_metric("algorithm", "differential_evolution")
    operation_logger.add_metric("data_shape", large_array.shape)  # Auto-compressed
    operation_logger.add_metric("convergence_data", convergence_history)  # Auto-compressed
    operation_logger.add_metric("final_parameters", optimized_params)
```

### Expected Output Examples

**Operation Summary Table**:
```
================================================================================
📋 ✅ Операция: Добавление серии данных (Время выполнения: 1.254s)
================================================================================
+----------------------+----------+--------------+-----------------+--------+-------+------------------+
| Sub-Operation        | Time     | Duration (s) | Component       | Status | Files | Heat Rates       |
+----------------------+----------+--------------+-----------------+--------+-------+------------------+
| GET_ALL_DATA         | 14:23:45 | 0.145        | file_data       | ✅     | 3     | 3, 5, 10         |
| Data Processing      | 14:23:45 | 0.089        | main_window     | ✅     | 3     | 3, 5, 10         |
| Plot Update          | 14:23:45 | 0.234        | plot_canvas     | ✅     | 3     | 3, 5, 10         |
| ADD_NEW_SERIES       | 14:23:45 | 0.567        | series_data     | ✅     | 3     | 3, 5, 10         |
| GET_SERIES           | 14:23:46 | 0.098        | series_data     | ✅     | 3     | 3, 5, 10         |
| UI Update            | 14:23:46 | 0.121        | main_window     | ✅     | 3     | 3, 5, 10         |
+----------------------+----------+--------------+-----------------+--------+-------+------------------+
Итог: ✅ | Время: 1.254s | Запросов: 3 | Файлов: 3 | Скорости: 3, 5, 10 K/min
```

**Scientific Computation Analysis**:
```
================================================================================
📊 Model-Free Analysis Results (Duration: 45.67s)
================================================================================
+-------------+----------+--------------+------------------+--------+---------+----------------+
| Reaction    | Method   | Duration (s) | Convergence      | Status | R²      | Data Points    |
+-------------+----------+--------------+------------------+--------+---------+----------------+
| reaction_0  | Friedman | 12.34        | 1.23e-6          | ✅     | 0.9876  | 100            |
| reaction_1  | KAS      | 15.67        | 2.45e-7          | ✅     | 0.9923  | 100            |
| reaction_2  | Starink  | 17.66        | 3.21e-6          | ⚠️     | 0.9654  | 95             |
+-------------+----------+--------------+------------------+--------+---------+----------------+
Summary: 3 reactions analyzed | Total time: 45.67s | Average R²: 0.9818
```

**Error Analysis with Context**:
```
================================================================================
❌ ERROR: Deconvolution Failed (Context Analysis)
================================================================================
Error: FileNotFoundError: deconvolution_results.json not found

Preceding Operations:
  14:23:40 | file_data        | Loading CSV data: NH4_rate_10.csv
  14:23:41 | calculations     | Starting deconvolution process  
  14:23:42 | optimization     | Differential evolution initiated

Context Analysis:
- File operation sequence suggests missing intermediate results
- Optimization process started but results file not created
- Previous successful runs indicate configuration change

Suggested Actions:
1. Check file permissions in results directory
2. Verify deconvolution parameters are valid
3. Examine optimization convergence logs
4. Consider re-running with increased iteration limit
```

---

## Architectural Benefits and Design Principles

### Performance Advantages

1. **Minimal Overhead**: Aggregation processing happens asynchronously with configurable buffering
2. **Adaptive Behavior**: System automatically adjusts processing based on load conditions
3. **Selective Processing**: Components can be enabled/disabled based on requirements
4. **Efficient Data Handling**: Automatic compression of large datasets in metrics
5. **Thread Safety**: All components designed for concurrent access in Qt applications

### Maintainability Features

1. **Modular Design**: Each component has clear responsibilities with minimal coupling
2. **Configuration-driven**: Behavior can be modified without code changes
3. **Backward Compatibility**: Existing logging continues to work without modification
4. **Extensible Architecture**: New pattern types and monitoring capabilities easily added
5. **Clear Interfaces**: Standardized APIs across all components

### Scientific Computing Integration

1. **Domain-specific Metrics**: Built-in support for scientific computation parameters
2. **Operation Correlation**: Links GUI actions to computational results
3. **Performance Analysis**: Detailed tracking of optimization and analysis operations
4. **Error Context**: Enhanced error analysis for scientific computation failures
5. **Data Compression**: Intelligent handling of large scientific datasets in logs

The log aggregation architecture provides a comprehensive, production-ready solution for monitoring and analyzing scientific computation workflows while maintaining the flexibility and performance required for real-time data analysis applications.
