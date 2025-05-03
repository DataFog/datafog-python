# Runtime Breakers
- [x] SparkService.__init__ — move field assignments above create_spark_session().
- [x] pyspark_udfs.ensure_installed — drop the stray self.
- [x] CLI enum mismatch — convert "scan" → [OperationType.SCAN].
- [x] Guard Donut: import torch/transformers only if use_donut is true.