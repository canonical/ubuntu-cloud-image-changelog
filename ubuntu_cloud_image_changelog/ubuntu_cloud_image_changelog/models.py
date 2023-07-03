from typing import List, Optional

from pydantic import BaseModel


class SnapSummary(BaseModel):
    added: Optional[List[str]] = []
    removed: Optional[List[str]] = []
    diff: Optional[List[str]] = []


class DebSummary(BaseModel):
    added: Optional[List[str]] = []
    removed: Optional[List[str]] = []
    diff: Optional[List[str]] = []


class Summary(BaseModel):
    snap: SnapSummary
    deb: DebSummary


class FromVersion(BaseModel):
    source_package_name: Optional[str] = None
    source_package_version: Optional[str] = None
    version: Optional[str] = None


class ToVersion(BaseModel):
    source_package_name: Optional[str] = None
    source_package_version: Optional[str] = None
    version: Optional[str] = None


class Cve(BaseModel):
    cve: str
    url: str
    cve_description: str
    cve_priority: str
    cve_public_date: str


class Change(BaseModel):
    cves: Optional[List[Cve]] = []
    log: List[str] = []
    package: str
    version: str
    urgency: str
    distributions: str
    launchpad_bugs_fixed: Optional[List[int]] = []
    author: str
    date: str


class DebPackage(BaseModel):
    name: str
    from_version: FromVersion
    to_version: ToVersion
    cves: Optional[List[Cve]] = []
    launchpad_bugs_fixed: Optional[List[int]] = []
    changes: Optional[List[Change]] = []
    notes: Optional[str] = None


class SnapPackage(BaseModel):
    name: str
    from_version: FromVersion
    to_version: ToVersion


class Diff(BaseModel):
    deb: List[DebPackage]
    snap: List[SnapPackage]


class Added(BaseModel):
    deb: List[DebPackage]
    snap: List[SnapPackage]


class Removed(BaseModel):
    deb: List[DebPackage]
    snap: List[SnapPackage]


class ChangelogModel(BaseModel):
    summary: Summary
    diff: Diff
    added: Added
    removed: Removed
    notes: Optional[str] = None
    from_series: str
    to_series: str
    from_serial: str = None
    to_serial: str = None
    from_manifest_filename: str
    to_manifest_filename: str
