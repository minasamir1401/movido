
import re

content = """
<HTML>
<HEAD>
<title>[Laroza Now] مشاهدة فيلم السادة الافاضل كامل اون لاين HD</title>
<link rel="stylesheet" href="/css/main.css">
<script src="/js/jquery.min.js" type="7680eadfcacdf9cc96518b9e-text/javascript"></script>
<script src="/js/xupload.js" type="7680eadfcacdf9cc96518b9e-text/javascript"></script>
<script src="/js/jquery.cookie.js" type="7680eadfcacdf9cc96518b9e-text/javascript"></script>
<script type="7680eadfcacdf9cc96518b9e-text/javascript">
$.cookie('file_id', '130897', { expires: 10 });
</script>
"""

script_pattern = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)

def script_filter(match):
    text = match.group(0).lower()
    if any(x in text for x in ['xupload.js', 'jquery.cookie.js', 'googletagmanager', 'disable adblock']):
        return f"<!-- Stripped Script: {text[:20]}... -->"
    return match.group(0)

new_content = script_pattern.sub(script_filter, content)

print("--- Result ---")
print(new_content)
if "xupload.js" not in new_content:
    print("\nSUCCESS: xupload.js removed")
else:
    print("\nFAILURE: xupload.js still present")
