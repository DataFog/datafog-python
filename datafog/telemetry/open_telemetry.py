import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from azure.monitor.opentelemetry import configure_azure_monitor
import platform
from opentelemetry.trace import Status, StatusCode

# Use environment variable if available, otherwise fall back to hardcoded value
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from logging import INFO, getLogger
from dotenv import load_dotenv
from azure.monitor.opentelemetry import configure_azure_monitor
load_dotenv()

APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

class Telemetry:
    def __init__(self):
        self.ready = False
        self.trace_set = False
        try:
            # Create a new TracerProvider and set it as the global trace provider
            tracer_provider = TracerProvider()
            trace.set_tracer_provider(tracer_provider)

            # Configure Azure Monitor with the connection string from environment variables
            configure_azure_monitor(connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING, logger_name="datafog_logger")

            # Create an exporter that sends data to Application Insights
            exporter = AzureMonitorTraceExporter(
                connection_string=APPLICATIONINSIGHTS_CONNECTION_STRING
            )

            # Create a span processor and add it to the tracer provider
            span_processor = BatchSpanProcessor(exporter)
            tracer_provider.add_span_processor(span_processor)

            # Get a tracer
            self.tracer = trace.get_tracer(__name__)

            self.ready = True
            self.trace_set = True

        except Exception as e:
            print(f"Error setting up Azure Monitor: {e}")



    def datafog_creation(self, name: str):
        if self.ready:
            try:
                tracer = trace.get_tracer(__name__)
                span = tracer.start_span("datafog object created")
                self._add_attribute(span, "datafog_name", name)
                self._add_attribute(span, "datafog_version", platform.python_version())
                span.set_status(Status(StatusCode.OK))
                span.end()
            except Exception as e:
                print(f"Error starting span: {e}")
                return None

    def _add_attribute(self, span, key, value):
        """Add an attribute to a span."""
        try:
            return span.set_attribute(key, value)
        except Exception:
            pass

