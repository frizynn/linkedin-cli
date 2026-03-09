"""Constants shared across linkedin-cli modules."""

APP_NAME = "linkedin-cli"
API_BASE_URL = "https://www.linkedin.com"
VOYAGER_API_BASE_URL = "https://www.linkedin.com/voyager/api"

ENV_CONFIG_PATH = "LINKEDIN_CONFIG"
ENV_PROXY = "LINKEDIN_PROXY"
ENV_LI_AT = "LINKEDIN_LI_AT"
ENV_JSESSIONID = "LINKEDIN_JSESSIONID"
ENV_COOKIE_HEADER = "LINKEDIN_COOKIE_HEADER"
ENV_BROWSER = "LINKEDIN_BROWSER"
ENV_HEADLESS = "LINKEDIN_HEADLESS"

DEFAULT_CONFIG_FILE_NAMES = ("config.yaml", "config.yml")
DEFAULT_FETCH_COUNT = 20
DEFAULT_FILTER_MODE = "recent"
DEFAULT_BROWSER = "chrome"
DEFAULT_TIMEOUT = 20.0
DEFAULT_REQUEST_DELAY = 1.25
DEFAULT_RETRY_BASE_DELAY = 3.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_WRITE_DELAY_MIN = 1.5
DEFAULT_WRITE_DELAY_MAX = 4.0

SUPPORTED_BROWSERS = (
    "chrome",
    "chromium",
    "brave",
    "edge",
    "firefox",
)

COOKIE_REQUIRED_NAMES = (
    "li_at",
    "JSESSIONID",
)

REACTION_TYPES = {
    "like": "LIKE",
    "celebrate": "PRAISE",
    "support": "APPRECIATION",
    "love": "EMPATHY",
    "insightful": "INTEREST",
    "curious": "ENTERTAINMENT",
}

VISIBILITY_OPTIONS = (
    "connections",
    "public",
)

DEFAULT_HEADERS = {
    "accept": "application/json",
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
}
