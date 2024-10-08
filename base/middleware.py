import json
import re

from django.conf import settings
from django.http import Http404


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.IS_ADMIN_ENABLED:
            admin_url = settings.ADMIN_SITE_URL_PATH

            # Check if the current URL matches the admin URL
            if request.path.startswith(admin_url):
                raise Http404()

        response = self.get_response(request)
        return response


class MinifyHTMLMiddleware:
    """
    Middleware that minifies the HTML, CSS, JS, and JSON-LD content of responses.
    It handles comments, unnecessary whitespace, and ensures that URLs and structured
    data are properly preserved during the process.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        content_type = response.get("Content-Type", "")
        if "text/html" in content_type:
            response.content = self.minify_html(
                response.content.decode("utf-8")
            ).encode("utf-8")
            response["Content-Length"] = str(len(response.content))

        return response

    def minify_html(self, html):
        """
        Minifies the HTML content by removing comments, reducing extra whitespace,
        and processing <script>, <style>, and <script type="application/ld+json"> tags.
        """

        # Remove HTML comments (but not IE conditional comments)
        html = re.sub(r"<!--(?!<!)[^\[>][\s\S]*?-->", "", html)

        # Minify CSS inside <style> tags
        html = re.sub(
            r"(<style[^>]*>)(.*?)(</style>)",
            self.minify_css,
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Minify JS inside <script> tags
        html = re.sub(
            r"(<script[^>]*>)(.*?)(</script>)",
            self.minify_js,
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Minify JSON-LD inside <script type="application/ld+json"> tags
        html = re.sub(
            r'(<script type="application/ld\+json">)(.*?)(</script>)',
            self.minify_json_ld,
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Remove extra whitespace between HTML tags
        html = re.sub(r">\s+<", "><", html)

        # Remove newlines, tabs, and extra spaces
        html = re.sub(r"\s+", " ", html)

        return html.strip()

    def minify_css(self, match):
        """
        Minifies CSS by removing comments and unnecessary whitespace.
        """
        style_tag, content, closing_tag = match.groups()
        # Remove CSS comments
        content = re.sub(r"/\*[\s\S]*?\*/", "", content)
        # Remove newlines, tabs, and extra spaces
        content = re.sub(r"\s+", " ", content)
        # Remove spaces around CSS rules
        content = re.sub(r"\s*([{:;}])\s*", r"\1", content)
        return f"{style_tag}{content.strip()}{closing_tag}"

    def minify_js(self, match):
        """
        Minifies JavaScript content by removing comments and preserving URLs.
        """
        script_tag, content, closing_tag = match.groups()

        # Preserve URLs in the JS by replacing them temporarily
        url_placeholders = {}

        def replace_url(m):
            placeholder = f"__URL_PLACEHOLDER_{len(url_placeholders)}__"
            url_placeholders[placeholder] = m.group(0)
            return placeholder

        content = re.sub(r"(https?:)?//[^\s/$.?#].[^\s]*", replace_url, content)

        # Remove single-line comments, except for those containing '://'
        content = re.sub(r"(?<!:)//.*?$", "", content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r"/\*[\s\S]*?\*/", "", content)
        # Remove extra spaces and newlines
        content = re.sub(r"\s+", " ", content)

        # Restore URLs
        for placeholder, url in url_placeholders.items():
            content = content.replace(placeholder, url)

        return f"{script_tag}{content.strip()}{closing_tag}"

    def minify_json_ld(self, match):
        """
        Minifies JSON-LD content by formatting it without extra whitespace.
        """
        script_tag, content, closing_tag = match.groups()
        try:
            # Parse and re-serialize the JSON to ensure no unnecessary whitespace
            minified_json = json.dumps(json.loads(content), separators=(",", ":"))
            return f"{script_tag}{minified_json}{closing_tag}"
        except json.JSONDecodeError:
            # If invalid JSON, return it as-is
            return match.group(0)
