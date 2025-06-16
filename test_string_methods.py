#!/usr/bin/env python3

import time

from src.core.log_aggregator.meta_operation import MetaOperation
from src.core.log_aggregator.sub_operation_log import SubOperationLog

# Create test SubOperationLog
sub_op = SubOperationLog(1, "GET_VALUE", "file_data", time.time())
sub_op.response_data_raw = "This large data should not appear in __str__ output"
print("SubOperationLog __str__:", str(sub_op))
print("SubOperationLog __repr__:", repr(sub_op))

# Create test MetaOperation
meta_op = MetaOperation("test_id", "TestStrategy", "Test description", [sub_op])
print("MetaOperation __str__:", str(meta_op))
print("MetaOperation name property:", meta_op.name)
