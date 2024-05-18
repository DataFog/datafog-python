import asyncio
import json
import logging
import os
import platform
from typing import Any

import pkg_resources
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode


class Telemetry:
    """A class to handle anonymous telemetry for the DataFog package."""

    def __init__(self, instrumentation_key: str = os.getenv("INSTRUMENTATION_KEY")):
        self.ready = False
        self.trace_set = False
        try:
            self.resource = Resource(attributes={SERVICE_NAME: "datafog-python"})
            self.provider = TracerProvider(resource=self.resource)
            exporter = AzureMonitorTraceExporter(
                connection_string=os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]
            )
            processor = BatchSpanProcessor(exporter)
            self.provider.add_span_processor(processor)
            self.ready = True
        except BaseException as e:
            if isinstance(
                e,
                (SystemExit, KeyboardInterrupt, GeneratorExit, asyncio.CancelledError),
            ):
                raise
            self.ready = False

    def set_tracer(self):
        """Sets the tracer for telemetry."""
        if self.ready:
            try:
                trace.set_tracer_provider(self.provider)
                self.trace_set = True
            except Exception:
                self.trace_set = False

    def log_system_info(self):
        """Logs system information."""
        if self.ready:
            try:
                tracer = trace.get_tracer("datafog.telemetry")
                with tracer.start_as_current_span("System Info") as span:
                    self._add_attribute(
                        span,
                        "datafog_version",
                        pkg_resources.get_distribution("datafog").version,
                    )
                    self._add_attribute(
                        span, "python_version", platform.python_version()
                    )
                    self._add_attribute(span, "os", platform.system())
                    self._add_attribute(span, "platform_version", platform.version())
                    self._add_attribute(span, "cpus", os.cpu_count())
                    span.set_status(Status(StatusCode.OK))
            except Exception:
                pass

    def pipeline_execution(self, datafog, input_data, output_data):
        """Records the execution of a DataFog pipeline."""
        if self.ready:
            try:
                tracer = trace.get_tracer("datafog.telemetry")
                with tracer.start_as_current_span("Pipeline Execution") as span:
                    self._add_attribute(
                        span,
                        "datafog_version",
                        pkg_resources.get_distribution("datafog").version,
                    )
                    self._add_attribute(
                        span, "pipeline_type", datafog.__class__.__name__
                    )
                    self._add_attribute(span, "input_data", input_data)
                    self._add_attribute(span, "output_data", output_data)
                    span.set_status(Status(StatusCode.OK))
            except Exception:
                pass

    def end_pipeline(self, datafog, output):
        if self.ready:
            try:
                tracer = trace.get_tracer("datafog.telemetry")
                with tracer.start_as_current_span("Pipeline Ended") as span:
                    self._add_attribute(
                        span,
                        "datafog_version",
                        pkg_resources.get_distribution("datafog").version,
                    )
                    self._add_attribute(
                        span, "pipeline_type", datafog.__class__.__name__
                    )
                    self._add_attribute(span, "output", output)
                    span.set_status(Status(StatusCode.OK))
            except Exception:
                pass

    def _add_attribute(self, span, key, value):
        """Add an attribute to a span."""
        try:
            span.set_attribute(key, value)
        except Exception:
            pass
