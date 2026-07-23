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
  <project_license>LicenseRef-proprietary</project_license>
  <name>"""
        + app_description
        + """</name>
  <summary>Professional Editing, Color, Effects and Audio Post!</summary>

  <description>
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
      <caption>DaVinci Resolve 18 Cut Page</caption>
      <image>https://images.blackmagicdesign.com/images/products/davinciresolve/overview/onesolution/carousel/cut.jpg</image>
    </screenshot>
    <screenshot>
      <caption>DaVinci Resolve 18 Edit Page</caption>
      <image>https://images.blackmagicdesign.com/images/products/davinciresolve/overview/onesolution/carousel/edit.jpg</image>
    </screenshot>
    <screenshot>
      <caption>DaVinci Resolve 18 Color Page</caption>
      <image>https://images.blackmagicdesign.com/images/products/davinciresolve/overview/onesolution/carousel/color.jpg</image>
    </screenshot>
    <screenshot>
      <caption>DaVinci Resolve 18 Fusion Page</caption>
      <image>https://images.blackmagicdesign.com/images/products/davinciresolve/overview/onesolution/carousel/fusion.jpg</image>
    </screenshot>
    <screenshot>
      <caption>DaVinci Resolve 18 Fairlight Page</caption>
      <image>https://images.blackmagicdesign.com/images/products/davinciresolve/overview/onesolution/carousel/fairlight.jpg</image>
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
