"""ANA MAX distributed runtime layer."""

__all__ = ["DistributedPipelineSkeleton", "PipelineReasoningHelper", "PipelineRecoveryPlanner"]


def __getattr__(name: str):
    if name == "DistributedPipelineSkeleton":
        from .distributed_pipeline import DistributedPipelineSkeleton

        return DistributedPipelineSkeleton
    if name == "PipelineReasoningHelper":
        from .pipeline_reasoning_helper import PipelineReasoningHelper

        return PipelineReasoningHelper
    if name == "PipelineRecoveryPlanner":
        from .pipeline_recovery import PipelineRecoveryPlanner

        return PipelineRecoveryPlanner
    raise AttributeError(name)
