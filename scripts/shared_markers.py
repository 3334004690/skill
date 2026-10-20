"""Machine-readable resource markers consumed by the host application."""

MARK_TAGS = {"image": "[[SKILL_IMAGE:{}]]", "video": "[[SKILL_VIDEO:{}]]", "audio": "[[SKILL_AUDIO:{}]]", "file": "[[SKILL_FILE:{}]]"}

def mark_url(url, resource_type="file"):
    return MARK_TAGS.get(resource_type, MARK_TAGS["file"]).format(url)
