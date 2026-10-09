"""What the jobs endpoints send back: response bodies, separate from the internal types."""

from typing import Self

from pydantic import BaseModel

from jobfinder.services.refresher import SourceRefresh


class SourceRefreshReport(BaseModel):
    """One job source after a refresh: how many jobs it has and how many are new, or its error."""

    source: str  # e.g. "greenhouse/datadog"
    job_count: int
    new_job_count: int
    error: str | None

    @classmethod
    def from_source_refresh(cls, source_refresh: SourceRefresh) -> Self:
        return cls(
            source=str(source_refresh.result.source),
            job_count=len(source_refresh.result.jobs),
            new_job_count=source_refresh.new_job_count,
            error=source_refresh.result.error,
        )


class RefreshReport(BaseModel):
    """Every job source after a refresh, and the totals."""

    sources: list[SourceRefreshReport]
    job_count: int
    new_job_count: int

    @classmethod
    def from_source_refreshes(cls, source_refreshes: list[SourceRefresh]) -> Self:
        source_reports = [
            SourceRefreshReport.from_source_refresh(source_refresh)
            for source_refresh in source_refreshes
        ]
        return cls(
            sources=source_reports,
            job_count=sum(report.job_count for report in source_reports),
            new_job_count=sum(report.new_job_count for report in source_reports),
        )
