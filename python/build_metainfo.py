import datetime
import json
import re

import requests
from resolve_download import Version

_RELATIVE_DAYS_AGO_RE = re.compile(r"^(\d+)\s+days?\s+ago$", re.IGNORECASE)


def _parse_download_date(raw: str) -> datetime.date:
    today = datetime.date.today()
    normalized = raw.strip().lower()
    if normalized == "today":
        return today
    if normalized == "yesterday":
        return today - datetime.timedelta(days=1)
    relative = _RELATIVE_DAYS_AGO_RE.match(normalized)
    if relative:
        return today - datetime.timedelta(days=int(relative.group(1)))
    return datetime.datetime.strptime(raw, "%d %b %Y").date()


def build_metainfo(app_id: str, app_description: str, app_tag: str):
    response = requests.get(
        "https://www.blackmagicdesign.com/api/support/en/downloads.json"
    )

    parsed_response = json.loads(response.content)

    latest_description = ""

    releases = ""
    for idx, download in enumerate(parsed_response["downloads"]):
        if (
            "Linux" not in download["urls"]
            or download["urls"]["Linux"][0]["product"] != app_tag
        ):
            continue

        linux = download["urls"]["Linux"][0]
        description = download["desc"]
        beta = re.compile(r".*Beta (\d+)").match(linux["downloadTitle"])
        version = Version(
            major=linux["major"],
            minor=linux["minor"],
            patch=linux["releaseNum"],
            build=linux["releaseId"],
            beta=-1 if beta is None or beta.group(1) == "" else beta.group(1),
        )
        date = _parse_download_date(download["date"]).strftime("%Y-%m-%d")

        if idx == 0 or latest_description == "":
            latest_description = description

        release = (
            """<release version=\""""
            + str(version)
            + """\" date=\""""
            + date
            + """\">
              <description>
                 """
            + description
            + """
              </description>
            </release>"""
        )

        releases += release

    template = (
        """<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>"""
        + app_id
        + """</id>
  <metadata_license>FSFAP</metadata_license>
  <project_license>LicenseRef-proprietary=https://d7umqicpi7263.cloudfront.net/eula/product/926e6a7e-46f0-465c-8182-ad56050c9094/d4d34663-7069-48ce-b0fa-57d3ddc00b6d.pdf</project_license>
  <name>"""
        + app_description
        + """</name>
  <developer id="com.blackmagic">
    <name>Blackmagic Design Pty Ltd.</name>
  </developer>
  <summary>Professional editing, color grading, visual effects, and audio post production in one application</summary>

  <description>
    <p>
      DaVinci Resolve combines editing, color correction, visual effects, motion
      graphics, and audio post production in a single application, so you can
      go from the first cut to the final master without switching software.
      It is used on Hollywood feature films, television shows, and commercials,
      and now the same tools are available to editors on every kind of project.
    </p>
    <p>
      The Cut and Edit pages provide fast, precise editing tools alongside
      traditional trimming, while the Color page offers node based grading with
      HDR support trusted by professional colorists. The Fusion page adds
      Hollywood style visual effects and motion graphics, and the Fairlight page
      brings a full digital audio workstation for mixing, editing, and mastering
      sound, all within one project.
    </p>
    <p>
      """
        + latest_description
        + """
    </p>
  </description>

  <launchable type="desktop-id">"""
        + app_id
        + """.desktop</launchable>

  <screenshots>
    <screenshot type="default">
      <caption>DaVinci Resolve Cut Page</caption>
      <image>https://cdn.blossomos.org/forgeassets/6544d7e8-7106-48a6-b28c-3e9f0c12f6c6.png</image>
    </screenshot>
    <screenshot>
      <caption>DaVinci Resolve Edit Page</caption>
      <image>https://cdn.blossomos.org/forgeassets/a32844aa-f01f-47f7-98dc-fd7a1c81b523.jpg</image>
    </screenshot>
    <screenshot>
      <caption>DaVinci Resolve Color Page</caption>
      <image>https://cdn.blossomos.org/forgeassets/999bbd61-f440-4e35-981e-a4bd6c0a9872.jpg</image>
    </screenshot>
    <screenshot>
      <caption>DaVinci Resolve Fusion Page</caption>
      <image>https://cdn.blossomos.org/forgeassets/62d204e2-6dea-4e83-ab83-cff2864adf69.jpg</image>
    </screenshot>
    <screenshot>
      <caption>DaVinci Resolve Fairlight Page</caption>
      <image>https://cdn.blossomos.org/forgeassets/4fef76c5-a614-4090-bd6d-398e9b3c7e13.jpg</image>
    </screenshot>
  </screenshots>

  <url type="homepage">https://www.blackmagicdesign.com/products/davinciresolve</url>
  <project_group>Blackmagicdesign</project_group>

  <provides>
    <binary>resolve</binary>
  </provides>

  <releases>
    """
        + releases
        + """
  </releases>
</component>
"""
    )
    with open(f"/app/share/metainfo/{app_id}.metainfo.xml", "w") as f:
        f.write(template)
