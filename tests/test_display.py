"""Tests for the display system."""

import pytest
import base64
import json
from unittest.mock import Mock, patch

from src.plaque.display import (
    display_as_html,
    _render_display_result,
    _render_mime_data,
    _try_ipython_reprs,
    _handle_builtin_types,
)


class TestDisplayAsHtml:
    """Test the main display_as_html function."""

    def test_display_method_priority(self):
        """Test that _display_() method takes priority."""

        class TestObject:
            def _display_(self):
                return "<h1>Custom Display</h1>"

            def _repr_html_(self):
                return "<p>HTML Repr</p>"

            def __repr__(self):
                return "TestObject()"

        obj = TestObject()
        result = display_as_html(obj)
        assert "<h1>Custom Display</h1>" in result
        assert "<p>HTML Repr</p>" not in result

    def test_mime_method_priority(self):
        """Test that _mime_() method takes priority over IPython methods."""

        class TestObject:
            def _mime_(self):
                return ("text/html", "<div>MIME HTML</div>")

            def _repr_html_(self):
                return "<p>HTML Repr</p>"

            def __repr__(self):
                return "TestObject()"

        obj = TestObject()
        result = display_as_html(obj)
        assert "<div>MIME HTML</div>" in result
        assert "<p>HTML Repr</p>" not in result

    def test_ipython_repr_fallback(self):
        """Test fallback to IPython _repr_*_ methods."""

        class TestObject:
            def _repr_html_(self):
                return "<p>HTML Repr</p>"

            def __repr__(self):
                return "TestObject()"

        obj = TestObject()
        result = display_as_html(obj)
        assert "<p>HTML Repr</p>" in result

    def test_builtin_types_fallback(self):
        """Test fallback to built-in type handling."""
        # Test with a basic object that should trigger builtin handling
        obj = "simple string"
        result = display_as_html(obj)
        assert "simple string" in result
        assert "result-output" in result

    def test_repr_fallback(self):
        """Test final fallback to repr()."""

        class SimpleObject:
            def __repr__(self):
                return "SimpleObject(42)"

        obj = SimpleObject()
        result = display_as_html(obj)
        assert "SimpleObject(42)" in result
        assert "result-output" in result


class TestDisplayMethod:
    """Test _display_() method handling."""

    def test_display_returns_string_html(self):
        """Test _display_() returning HTML string."""

        class TestObject:
            def _display_(self):
                return "<div class='custom'>Custom HTML</div>"

        obj = TestObject()
        result = display_as_html(obj)
        assert "<div class='custom'>Custom HTML</div>" in result

    def test_display_returns_string_plain(self):
        """Test _display_() returning plain string."""

        class TestObject:
            def _display_(self):
                return "Plain text result"

        obj = TestObject()
        result = display_as_html(obj)
        assert "Plain text result" in result
        assert "result-output" in result

    def test_display_returns_object(self):
        """Test _display_() returning another object (recursive)."""

        class InnerObject:
            def _repr_html_(self):
                return "<span>Inner HTML</span>"

        class TestObject:
            def _display_(self):
                return InnerObject()

        obj = TestObject()
        result = display_as_html(obj)
        assert "<span>Inner HTML</span>" in result

    def test_display_method_exception(self):
        """Test _display_() method raising exception."""

        class TestObject:
            def _display_(self):
                raise ValueError("Display error")

            def __repr__(self):
                return "TestObject()"

        obj = TestObject()
        result = display_as_html(obj)
        assert "TestObject()" in result


class TestMimeMethod:
    """Test _mime_() method handling."""

    def test_mime_text_html(self):
        """Test _mime_() returning HTML."""

        class TestObject:
            def _mime_(self):
                return ("text/html", "<b>Bold text</b>")

        obj = TestObject()
        result = display_as_html(obj)
        assert "<b>Bold text</b>" in result

    def test_mime_text_plain(self):
        """Test _mime_() returning plain text."""

        class TestObject:
            def _mime_(self):
                return ("text/plain", "Plain text content")

        obj = TestObject()
        result = display_as_html(obj)
        assert "Plain text content" in result
        assert "result-output" in result

    def test_mime_image_png(self):
        """Test _mime_() returning PNG image."""
        test_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

        class TestObject:
            def _mime_(self):
                return ("image/png", test_data)

        obj = TestObject()
        result = display_as_html(obj)
        assert f"data:image/png;base64,{test_data}" in result
        assert "mime-image" in result

    def test_mime_application_json(self):
        """Test _mime_() returning JSON."""

        class TestObject:
            def _mime_(self):
                return ("application/json", '{"key": "value"}')

        obj = TestObject()
        result = display_as_html(obj)
        assert "{&quot;key&quot;: &quot;value&quot;}" in result  # JSON is HTML-escaped
        assert "json-output" in result

    def test_mime_unknown_type(self):
        """Test _mime_() returning unknown MIME type."""

        class TestObject:
            def _mime_(self):
                return ("application/unknown", "some data")

        obj = TestObject()
        result = display_as_html(obj)
        assert "some data" in result
        assert "result-output" in result

    def test_mime_method_exception(self):
        """Test _mime_() method raising exception."""

        class TestObject:
            def _mime_(self):
                raise ValueError("MIME error")

            def __repr__(self):
                return "TestObject()"

        obj = TestObject()
        result = display_as_html(obj)
        assert "TestObject()" in result


class TestIpythonReprMethods:
    """Test IPython _repr_*_ method handling."""

    def test_repr_html(self):
        """Test _repr_html_() method."""

        class TestObject:
            def _repr_html_(self):
                return "<em>Emphasized text</em>"

        obj = TestObject()
        result = display_as_html(obj)
        assert "<em>Emphasized text</em>" in result

    def test_repr_svg(self):
        """Test _repr_svg_() method."""
        svg_content = '<svg><circle cx="50" cy="50" r="40"/></svg>'

        class TestObject:
            def _repr_svg_(self):
                return svg_content

        obj = TestObject()
        result = display_as_html(obj)
        assert svg_content in result
        assert "svg-output" in result

    def test_repr_png_bytes(self):
        """Test _repr_png_() method returning bytes."""
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"

        class TestObject:
            def _repr_png_(self):
                return png_bytes

        obj = TestObject()
        result = display_as_html(obj)
        expected_b64 = base64.b64encode(png_bytes).decode()
        assert f"data:image/png;base64,{expected_b64}" in result
        assert "png-output" in result

    def test_repr_png_string(self):
        """Test _repr_png_() method returning base64 string."""
        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

        class TestObject:
            def _repr_png_(self):
                return png_b64

        obj = TestObject()
        result = display_as_html(obj)
        assert f"data:image/png;base64,{png_b64}" in result
        assert "png-output" in result

    def test_repr_jpeg(self):
        """Test _repr_jpeg_() method."""
        jpeg_b64 = "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwDX8A=="

        class TestObject:
            def _repr_jpeg_(self):
                return jpeg_b64

        obj = TestObject()
        result = display_as_html(obj)
        assert f"data:image/jpeg;base64,{jpeg_b64}" in result
        assert "jpeg-output" in result

    def test_repr_markdown(self):
        """Test _repr_markdown_() method."""
        with patch(
            "src.plaque.formatter.format_markdown",
            return_value="<h1>Markdown Header</h1>",
        ) as mock_format_markdown:

            class TestObject:
                def _repr_markdown_(self):
                    return "# Markdown Header"

            obj = TestObject()
            result = display_as_html(obj)
            assert "<h1>Markdown Header</h1>" in result
            assert "markdown-output" in result
            mock_format_markdown.assert_called_once_with("# Markdown Header")

    def test_repr_latex(self):
        """Test _repr_latex_() method."""

        class TestObject:
            def _repr_latex_(self):
                return "E = mc^2"

        obj = TestObject()
        result = display_as_html(obj)
        assert "\\[E = mc^2\\]" in result
        assert "math-block" in result

    def test_repr_json(self):
        """Test _repr_json_() method."""
        test_data = {"name": "test", "value": 42}

        class TestObject:
            def _repr_json_(self):
                return test_data

        obj = TestObject()
        result = display_as_html(obj)
        # JSON is HTML-escaped
        assert "&quot;name&quot;: &quot;test&quot;" in result
        assert "&quot;value&quot;: 42" in result
        assert "json-output" in result

    def test_repr_method_priority(self):
        """Test that _repr_html_() takes priority over other _repr_*_ methods."""

        class TestObject:
            def _repr_html_(self):
                return "<p>HTML priority</p>"

            def _repr_svg_(self):
                return "<svg>SVG content</svg>"

            def _repr_png_(self):
                return "png_data"

        obj = TestObject()
        result = display_as_html(obj)
        assert "<p>HTML priority</p>" in result
        assert "SVG content" not in result

    def test_repr_method_exception(self):
        """Test _repr_*_ method raising exception."""

        class TestObject:
            def _repr_html_(self):
                raise ValueError("HTML error")

            def _repr_svg_(self):
                return "<svg>Fallback SVG</svg>"

        obj = TestObject()
        result = display_as_html(obj)
        assert "<svg>Fallback SVG</svg>" in result
        assert "svg-output" in result


class TestBuiltinTypes:
    """Test built-in type handling."""

    def test_builtin_types_no_match(self):
        """Test that objects not matching built-in types return None."""

        class CustomObject:
            pass

        obj = CustomObject()
        result = _handle_builtin_types(obj)
        assert result is None


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_none_object(self):
        """Test display of None."""
        result = display_as_html(None)
        assert "None" in result
        assert "result-output" in result

    def test_empty_string(self):
        """Test display of empty string."""
        result = display_as_html("")
        assert "result-output" in result

    def test_complex_object(self):
        """Test object with multiple display methods."""

        class ComplexObject:
            def _display_(self):
                return self

            def _repr_html_(self):
                return "<div>Complex HTML</div>"

            def __repr__(self):
                return "ComplexObject()"

        # This should cause infinite recursion protection
        obj = ComplexObject()
        # The _display_ method returns self, which should eventually fall back to _repr_html_
        result = display_as_html(obj)
        # Due to recursion, this might hit the repr fallback
        assert "ComplexObject()" in result or "<div>Complex HTML</div>" in result
