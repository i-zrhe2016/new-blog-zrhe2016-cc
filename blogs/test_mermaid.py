from django.test import SimpleTestCase

from blogs.templatetags.custom_tags import markdown


class MermaidMarkdownTests(SimpleTestCase):
    def test_mermaid_fence_renders_as_mermaid_pre(self):
        html = markdown('```mermaid\ngraph TD;\n    A-->B;\n```')

        self.assertIn('<pre class="mermaid">', html)
        self.assertIn('graph TD;', html)
        self.assertIn('A--&gt;B;', html)

    def test_mermaid_fence_does_not_use_syntax_highlighting(self):
        html = markdown('```mermaid\ngraph TD;\n    A-->B;\n```')

        self.assertNotIn('highlight', html)

    def test_mermaid_source_is_html_escaped(self):
        html = markdown('```mermaid\ngraph TD;\n    A["<script>alert(1)</script>"]-->B;\n```')

        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_tilde_fence_with_mermaid_info_is_rendered(self):
        html = markdown('~~~mermaid\ngraph LR;\n    A-->B;\n~~~')

        self.assertIn('<pre class="mermaid">', html)

    def test_other_fences_keep_syntax_highlighting(self):
        html = markdown('```python\nprint("hi")\n```')

        self.assertIn('highlight', html)
