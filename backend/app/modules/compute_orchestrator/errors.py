"""Transport failures are distinct from scientific FindingState values."""


class ComputeUnavailable(RuntimeError):
    pass


class ComputeTimeout(ComputeUnavailable):
    pass


class InvalidComputeResult(ComputeUnavailable):
    pass
