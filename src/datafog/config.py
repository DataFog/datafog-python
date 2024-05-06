from enum import Enum
from typing import Optional

from pydantic import BaseModel


class PipelineOperationType(Enum):
    READ_IMAGE = "read_image"
    PARSE_IMAGE = "parse_image"
    TEXT_PII_ANNOTATION = "text_pii_annotation"
    TEXT_PII_ANNOTATION_WITH_IMAGE = "text_pii_annotation_with_image"


class ModelConfig(BaseModel):
    model: str
    processor: str


class OperationConfig(BaseModel):
    operation_type: PipelineOperationType
    config: Optional[ModelConfig] = None

    @classmethod
    def model_validator(cls, v, values):
        configs = {
            "read_image": ModelConfig(
                model="naver-clova-ix/donut-base-finetuned-rvlcdip",
                processor="naver-clova-ix/donut-base-finetuned-rvlcdip",
            ),
            "parse_image": ModelConfig(
                model="naver-clova-ix/donut-base-finetuned-cord-v2",
                processor="naver-clova-ix/donut-base-finetuned-cord-v2",
            ),
        }
        operation_type = values.get("operation_type")
        if operation_type and operation_type.value in configs:
            return configs[operation_type.value]
        return v

    class Config:
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
